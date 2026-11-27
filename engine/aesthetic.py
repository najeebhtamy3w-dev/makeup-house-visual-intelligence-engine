"""Learned aesthetic predictor; requires matching ViT-L/14 embeddings and trusted local weights."""
import hashlib
from pathlib import Path
import math

class AestheticPredictor:
    def __init__(self,encoder,weights,expected_sha256):
        import torch
        if encoder.architecture!='ViT-L-14':
            raise ValueError('AESTHETIC_ENCODER_MISMATCH')
        path=Path(weights)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha256:
            raise ValueError('AESTHETIC_WEIGHT_HASH_MISMATCH')
        state=torch.load(path,map_location='cpu',weights_only=True)
        self.head=torch.nn.Linear(768,1)
        self.head.load_state_dict(state,strict=True)
        self.head.eval()
        self.encoder=encoder
        self.weight_sha256=expected_sha256

    def evaluate(self,image):
        import torch
        with torch.inference_mode():
            embedding=self.encoder.encode(image).float().cpu()
            score=float(self.head(embedding).item())
        if not math.isfinite(score):
            raise ValueError('INVALID_AESTHETIC_SCORE')
        return {'status':'EVALUATED','raw_score':score,'score':max(0,min(1,score/10)), 'weight_sha256':self.weight_sha256,'commercial_approved':False}
