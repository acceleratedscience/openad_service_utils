
from simple_implementation import MySimpleGenerator
from classic_implementation import MyClassicGenerator
from openad_service_utils import start_server

# register the function in global scope
MySimpleGenerator.register()
MyClassicGenerator.register()

if __name__ == "__main__":
    # start the server
    start_server(port=8080)
