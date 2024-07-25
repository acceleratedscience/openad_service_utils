

from implementation import MySimplePredictor
from openad_service_utils import start_server

# register the function in global scope
MySimplePredictor.register()

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
