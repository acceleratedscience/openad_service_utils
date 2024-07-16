

if __name__ == "__main__":
    from simple_implementation import MySimpleGenerator
    from classic_implementation import MyClassicGenerator
    MySimpleGenerator.register()
    MyClassicGenerator.register()
    
    # start the server
    from openad_service_utils import start_server
    start_server(port=8080)
