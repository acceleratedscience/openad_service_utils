from simple_implementation import MySimpleGenerator
from openad_service_utils import start_server

# register the function in global scope
MySimpleGenerator.register(no_model=True)

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
