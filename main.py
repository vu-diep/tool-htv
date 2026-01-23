from agent import StartApp

if __name__ == '__main__':
    try:
        app = StartApp()
        socket_server = app.ws_client.sio
        app.start()
    except Exception as e:
        print(f"Error when start application: {e}")