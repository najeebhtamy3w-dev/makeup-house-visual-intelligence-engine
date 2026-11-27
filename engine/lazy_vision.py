import time

class LazyVision:
    def __init__(self,factory):
        self.factory=factory
        self.model=None
    def identify(self,image):
        start=time.monotonic()
        cold=self.model is None
        if cold:
            self.model=self.factory()
        load=time.monotonic()-start if cold else 0.0
        start=time.monotonic()
        result=dict(self.model.identify(image))
        result['vision_runtime']={'cold_start':cold,'load_seconds':load,'inference_seconds':time.monotonic()-start}
        return result
