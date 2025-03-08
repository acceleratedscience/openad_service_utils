#!/usr/bin/env python
"""
Example client for the OpenAD asynchronous inference API.

This script demonstrates how to submit asynchronous requests, check their status,
and retrieve results using the enhanced asynchronous inference system.
"""

import argparse
import json
import time
import requests
import sys
from typing import Dict, Any, Optional, List
from pprint import pprint


def submit_async_request(
    base_url: str,
    service_type: str,
    service_name: str,
    parameters: Dict[str, Any],
    priority: str = "normal",
    timeout_seconds: Optional[int] = None
) -> str:
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
        The request ID
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
    
    response = requests.post(f"{base_url}/service", json=request_data)
    response.raise_for_status()
    
    result = response.json()
    if "request_id" not in result:
        raise ValueError(f"Unexpected response: {result}")
    
    return result["request_id"]


def get_request_status(base_url: str, request_id: str) -> Dict[str, Any]:
    """
    Get the status of an asynchronous request.
    
    Args:
        base_url: Base URL of the OpenAD API
        request_id: The request ID
        
    Returns:
        The request status
    """
    response = requests.get(f"{base_url}/async/status/{request_id}")
    response.raise_for_status()
    
    return response.json()


def cancel_request(base_url: str, request_id: str) -> Dict[str, Any]:
    """
    Cancel an asynchronous request.
    
    Args:
        base_url: Base URL of the OpenAD API
        request_id: The request ID
        
    Returns:
        The result of the cancellation
    """
    response = requests.delete(f"{base_url}/async/status/{request_id}")
    response.raise_for_status()
    
    return response.json()


def get_system_stats(base_url: str) -> Dict[str, Any]:
    """
    Get statistics about the asynchronous inference system.
    
    Args:
        base_url: Base URL of the OpenAD API
        
    Returns:
        System statistics
    """
    response = requests.get(f"{base_url}/async/stats")
    response.raise_for_status()
    
    return response.json()


def wait_for_completion(
    base_url: str,
    request_id: str,
    poll_interval: float = 1.0,
    max_wait_time: Optional[float] = None
) -> Dict[str, Any]:
    """
    Wait for an asynchronous request to complete.
    
    Args:
        base_url: Base URL of the OpenAD API
        request_id: The request ID
        poll_interval: Interval between status checks in seconds
        max_wait_time: Maximum time to wait in seconds
        
    Returns:
        The final request status
    """
    start_time = time.time()
    
    while True:
        status = get_request_status(base_url, request_id)
        
        if status["status"] in ("completed", "failed", "timeout", "canceled"):
            return status
        
        if max_wait_time is not None and time.time() - start_time > max_wait_time:
            print(f"Reached maximum wait time of {max_wait_time} seconds")
            return status
        
        time.sleep(poll_interval)


def main():
    parser = argparse.ArgumentParser(description="OpenAD Asynchronous Inference Client Example")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the OpenAD API")
    parser.add_argument("--service-type", default="get_molecule_property", help="Service type")
    parser.add_argument("--service-name", default="molecule_property", help="Service name")
    parser.add_argument("--property-type", default="logp", help="Property type")
    parser.add_argument("--subject", default="CC(=O)OC1=CC=CC=C1C(=O)O", help="Subject (e.g., SMILES string)")
    parser.add_argument("--priority", default="normal", choices=["low", "normal", "high", "critical"], help="Request priority")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--poll-interval", type=float, default=1.0, help="Interval between status checks in seconds")
    parser.add_argument("--max-wait-time", type=float, default=60.0, help="Maximum time to wait for completion in seconds")
    parser.add_argument("--stats", action="store_true", help="Get system statistics")
    parser.add_argument("--cancel", help="Cancel a request with the specified ID")
    
    args = parser.parse_args()
    
    # Get system statistics if requested
    if args.stats:
        print("Getting system statistics...")
        stats = get_system_stats(args.url)
        print("\nSystem Statistics:")
        pprint(stats)
        return
    
    # Cancel a request if requested
    if args.cancel:
        print(f"Canceling request {args.cancel}...")
        result = cancel_request(args.url, args.cancel)
        print("\nCancellation Result:")
        pprint(result)
        return
    
    # Submit a new request
    parameters = {
        "property_type": [args.property_type],
        "subjects": [args.subject],
        "subject_type": "smiles"
    }
    
    print(f"Submitting asynchronous request for {args.service_type}/{args.service_name}...")
    print(f"Parameters: {parameters}")
    print(f"Priority: {args.priority}")
    print(f"Timeout: {args.timeout if args.timeout else 'None'}")
    
    try:
        request_id = submit_async_request(
            base_url=args.url,
            service_type=args.service_type,
            service_name=args.service_name,
            parameters=parameters,
            priority=args.priority,
            timeout_seconds=args.timeout
        )
        
        print(f"\nRequest submitted successfully with ID: {request_id}")
        
        print("\nWaiting for completion...")
        final_status = wait_for_completion(
            base_url=args.url,
            request_id=request_id,
            poll_interval=args.poll_interval,
            max_wait_time=args.max_wait_time
        )
        
        print("\nFinal Status:")
        pprint(final_status)
        
        if final_status["status"] == "completed":
            print("\nRequest completed successfully!")
            if "result" in final_status:
                print("\nResult:")
                pprint(final_status["result"])
        else:
            print(f"\nRequest did not complete successfully. Status: {final_status['status']}")
            if "error" in final_status:
                print(f"Error: {final_status['error']}")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
