""" This is a dummy Classifier for the demonstration """


# this is just a Dummy Class for Demonstration Purposes
class ClassificationModel:
    """Does nothing. example for a torch model"""

    model = None

    def __init__(self, model, model_path, tokenizer) -> None:
        print("Path for Model " + str(model_path))
        self.model = model
        pass

    def to(self, *args, **kwargs):
        pass

    def eval(self, *args, **kwargs):

        return self.model
