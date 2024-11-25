# This code is designed to handle asynch requests
from fastapi import BackgroundTasks
import multiprocessing as mp

import asyncio
import uuid
import json
import pandas

POOL = None


def background_route_service(requestor, restful_request):
    global POOL
    print("in background)")
    if POOL is None:
        POOL = mp.Pool(processes=1)
    url = __create_job_url__(restful_request)
    POOL.apply_async(___call_service___, [restful_request, requestor, url], callback=finished)
    ___write_job_header_file__(restful_request, url)
    return {"id": url}


def finished():
    print("finished")


def list_async_jobs() -> dict:

    return


def retrieve_job(url) -> dict:
    try:
        print(f"retrieving /tmp/{url}.result")
        with open(f"/tmp/{url}.result", "r") as fd:
            return json.load(fd)
    except Exception as e:
        print(e)
        return None


def __create_job_url__(restful_request) -> str:
    url = uuid.uuid1()
    return url


def ___write_job_header_file__(restful_request, url) -> str:
    with open(f"/tmp/{url}.request", "w") as fd:
        fd.write(json.dumps(restful_request))
        fd.close()
    return url


def ___call_service___(restful_request: dict, requestor, url):
    with open(f"/tmp/{url}.running", "w") as fd:
        fd.write("")
        fd.close()
    try:
        result = requestor.route_service(restful_request)
        with open(f"/tmp/{url}.running", "w") as fd:
            fd.write(str(result))
            fd.close()
        with open(f"/tmp/{url}.running", "w") as fd:
            fd.write("run")
            fd.close()
    except Exception as e:
        result = {"error": str(e)}
        with open(f"/tmp/{url}.running", "w") as fd:
            fd.write(str(result))
            fd.close()
    try:
        with open(f"/tmp/{url}.result", "w") as fd:
            if isinstance(result, pandas.DataFrame):
                result = result.to_json()
            fd.write(json.dumps(result))
            fd.close()
    except Exception as e:
        result = {"error": str(e)}
        with open(f"/tmp/{url}.result", "w") as fd:
            fd.write(json.dumps(result))
            fd.close()
