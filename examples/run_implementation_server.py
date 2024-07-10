

if __name__ == "__main__":
    # first import the model to load into registry
    from template_implementation import MyModelGenerator
    # start the server
    from openad_service_utils.api.server import start_server
    start_server(port=8090)