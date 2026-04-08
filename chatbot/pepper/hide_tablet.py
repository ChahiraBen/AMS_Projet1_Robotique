import qi
app = qi.Application(["hide", "--qi-url", "tcp://127.0.0.1:9559"])
app.start()
app.session.service("ALTabletService").hideWebview()
print("Tablette effacee.")
app.stop()
