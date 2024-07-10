

if __name__ == "__main__":
    from template_implementation import MyModelGenerator
    from openad_service_utils.api.server import start_server
    start_server(port=8090)