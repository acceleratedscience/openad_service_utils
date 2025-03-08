#!/usr/bin/env python
"""
Load testing script for the OpenAD asynchronous inference API.

This script submits multiple asynchronous requests in parallel to test the
performance and reliability of the asynchronous inference system under load.
"""

import argparse
import json
import time
import requests
import sys
import threading
import random
import uuid
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint


def submit_async_request(
    base_url: str,
    service_type: str,
    service_name: str,
    parameters: Dict[str, Any],
    priority: str = "normal",
    timeout_seconds: Optional[int] = None
) -> Tuple[str, float]:
    """
    Submit an asynchronous request to the OpenAD API.
    
    Args:
        base_url: Base URL of the OpenAD API
        service_type: Type of service (e.g., "get_molecule_property")
        service_name: Name of the service
        parameters: Service parameters
        priority: Priority level ("low", "normal", "high", "critical")
        timeout_seconds: Optional timeout in seconds
        
    Returns:
        Tuple of (request_id, submit_time)
    """
    request_data = {
        "service_type": service_type,
        "service_name": service_name,
        "parameters": parameters,
        "async": True,
        "use_enhanced_async": True,
        "priority": priority
    }
    
    if timeout_seconds is not None:
        request_data["timeout_seconds"] = timeout_seconds
    
    start_time = time.time()
    response = requests.post(f"{base_url}/service", json=request_data)
    response.raise_for_status()
    
    result = response.json()
    if "request_id" not in result:
        raise ValueError(f"Unexpected response: {result}")
    
    return result["request_id"], start_time


def monitor_request(
    base_url: str,
    request_id: str,
    submit_time: float,
    poll_interval: float = 1.0,
    max_wait_time: Optional[float] = None,
    results: Dict[str, Dict[str, Any]] = None
):
    """
    Monitor an asynchronous request until completion.
    
    Args:
        base_url: Base URL of the OpenAD API
        request_id: The request ID
        submit_time: Time when the request was submitted
        poll_interval: Interval between status checks in seconds
        max_wait_time: Maximum time to wait in seconds
        results: Dictionary to store results
    """
    start_time = time.time()
    poll_count = 0
    
    while True:
        try:
            poll_count += 1
            response = requests.get(f"{base_url}/async/status/{request_id}")
            response.raise_for_status()
            
            status = response.json()
            current_time = time.time()
            elapsed = current_time - start_time
            
            if status["status"] in ("completed", "failed", "timeout", "canceled"):
                # Request is done
                end_time = time.time()
                total_time = end_time - submit_time
                
                if results is not None:
                    results[request_id] = {
                        "request_id": request_id,
                        "status": status["status"],
                        "total_time": total_time,
                        "poll_count": poll_count,
                        "result": status.get("result"),
                        "error": status.get("error")
                    }
                
                print(f"Request {request_id} {status['status']} in {total_time:.2f}s")
                break
            
            if max_wait_time is not None and elapsed > max_wait_time:
                # Timeout
                if results is not None:
                    results[request_id] = {
                        "request_id": request_id,
                        "status": "client_timeout",
                        "total_time": elapsed,
                        "poll_count": poll_count
                    }
                
                print(f"Request {request_id} timed out after {elapsed:.2f}s")
                break
            
            time.sleep(poll_interval)
        except Exception as e:
            print(f"Error monitoring request {request_id}: {e}")
            if results is not None:
                results[request_id] = {
                    "request_id": request_id,
                    "status": "error",
                    "error": str(e),
                    "poll_count": poll_count
                }
            break


def run_load_test(
    base_url: str,
    num_requests: int,
    concurrency: int,
    service_type: str,
    service_name: str,
    property_types: List[str],
    subjects: List[str],
    priorities: List[str] = ["normal"],
    timeout_seconds: Optional[int] = None,
    poll_interval: float = 1.0,
    max_wait_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Run a load test by submitting multiple requests in parallel.
    
    Args:
        base_url: Base URL of the OpenAD API
        num_requests: Number of requests to submit
        concurrency: Maximum number of concurrent requests
        service_type: Type of service
        service_name: Name of the service
        property_types: List of property types to use
        subjects: List of subjects to use
        priorities: List of priorities to use
        timeout_seconds: Optional timeout in seconds
        poll_interval: Interval between status checks in seconds
        max_wait_time: Maximum time to wait for completion in seconds
        
    Returns:
        Dictionary with test results
    """
    results = {}
    start_time = time.time()
    
    # Create a thread pool for submitting requests
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Submit requests
        futures = []
        for i in range(num_requests):
            # Select random property type and subject
            property_type = random.choice(property_types)
            subject = random.choice(subjects)
            priority = random.choice(priorities)
            
            # Prepare parameters
            parameters = {
                "property_type": [property_type],
                "subjects": [subject],
                "subject_type": "smiles"
            }
            
            # Submit the request
            future = executor.submit(
                submit_async_request,
                base_url=base_url,
                service_type=service_type,
                service_name=service_name,
                parameters=parameters,
                priority=priority,
                timeout_seconds=timeout_seconds
            )
            futures.append(future)
        
        # Wait for all requests to be submitted
        request_ids = []
        for future in futures:
            try:
                request_id, submit_time = future.result()
                request_ids.append((request_id, submit_time))
                print(f"Submitted request {request_id}")
            except Exception as e:
                print(f"Error submitting request: {e}")
    
    # Monitor requests
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        # Monitor each request
        for request_id, submit_time in request_ids:
            executor.submit(
                monitor_request,
                base_url=base_url,
                request_id=request_id,
                submit_time=submit_time,
                poll_interval=poll_interval,
                max_wait_time=max_wait_time,
                results=results
            )
    
    # Calculate statistics
    end_time = time.time()
    total_time = end_time - start_time
    
    completed_count = sum(1 for r in results.values() if r["status"] == "completed")
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")
    timeout_count = sum(1 for r in results.values() if r["status"] in ("timeout", "client_timeout"))
    error_count = sum(1 for r in results.values() if r["status"] == "error")
    
    completion_times = [r["total_time"] for r in results.values() if "total_time" in r]
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    min_completion_time = min(completion_times) if completion_times else 0
    max_completion_time = max(completion_times) if completion_times else 0
    
    stats = {
        "total_requests": num_requests,
        "completed_requests": completed_count,
        "failed_requests": failed_count,
        "timeout_requests": timeout_count,
        "error_requests": error_count,
        "total_time": total_time,
        "requests_per_second": num_requests / total_time,
        "avg_completion_time": avg_completion_time,
        "min_completion_time": min_completion_time,
        "max_completion_time": max_completion_time,
    }
    
    return {
        "stats": stats,
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="OpenAD Asynchronous Inference Load Test")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the OpenAD API")
    parser.add_argument("--num-requests", type=int, default=10, help="Number of requests to submit")
    parser.add_argument("--concurrency", type=int, default=5, help="Maximum number of concurrent requests")
    parser.add_argument("--service-type", default="get_molecule_property", help="Service type")
    parser.add_argument("--service-name", default="molecule_property", help="Service name")
    parser.add_argument("--property-types", default="logp", help="Comma-separated list of property types")
    parser.add_argument("--subjects-file", help="File containing SMILES strings (one per line)")
    parser.add_argument("--subject", default="CC(=O)OC1=CC=CC=C1C(=O)O", help="Default subject if no file is provided")
    parser.add_argument("--priorities", default="normal", help="Comma-separated list of priorities (low, normal, high, critical)")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Interval between status checks in seconds")
    parser.add_argument("--max-wait-time", type=float, default=300.0, help="Maximum time to wait for completion in seconds")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Parse property types
    property_types = args.property_types.split(",")
    
    # Parse priorities
    priorities = args.priorities.split(",")
    
    # Load subjects
    if args.subjects_file:
        with open(args.subjects_file, "r") as f:
            subjects = [line.strip() for line in f if line.strip()]
    else:
        subjects = [args.subject]
    
    print(f"Running load test with {args.num_requests} requests, {args.concurrency} concurrency")
    print(f"Service: {args.service_type}/{args.service_name}")
    print(f"Property types: {property_types}")
    print(f"Number of subjects: {len(subjects)}")
    print(f"Priorities: {priorities}")
    
    try:
        results = run_load_test(
            base_url=args.url,
            num_requests=args.num_requests,
            concurrency=args.concurrency,
            service_type=args.service_type,
            service_name=args.service_name,
            property_types=property_types,
            subjects=subjects,
            priorities=priorities,
            timeout_seconds=args.timeout,
            poll_interval=args.poll_interval,
            max_wait_time=args.max_wait_time
        )
        
        print("\nLoad Test Results:")
        pprint(results["stats"])
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed results saved to {args.output}")
    
    except Exception as e:
        print(f"Error running load test: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
