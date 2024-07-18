

if __name__ == "__main__":
    # start the server
    from implementation import MySimplePredictor
    MySimplePredictor.register()
    from openad_service_utils import start_server
    start_server(port=8080)
