

if __name__ == "__main__":
    # first import the model configuration
    # from simple_implementation import MyModelGenerator
    # from template_implementation import MyModelGenerator
    from single_implementation import MyModelGenerator
    MyModelGenerator.register()
    
    # start the server
    from openad_service_utils import start_server
    start_server(port=8080)
