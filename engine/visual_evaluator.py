"""Local model inference adapter; classification and similarity are hypotheses."""
from pathlib import Path
from PIL import Image
from .aesthetic import AestheticPredictor

PROMPTS={'packshot':'a studio product packaging photo on plain background','lifestyle':'a cosmetic product in a lifestyle scene','advertising':'a cosmetic advertising campaign image','detail':'a close up of product packaging details','texture':'a cosmetic cream or liquid texture','swatch':'cosmetic color swatches','group':'a group of multiple cosmetic products','logo':'a standalone brand logo','unrelated':'an image unrelated to cosmetic products'}

class LocalClip:
    def __init__(self,weights,device='cpu'):
        import open_clip
        import torch
        if not Path(weights).is_file(): raise FileNotFoundError('LOCAL_CLIP_WEIGHTS_REQUIRED')
        self.architecture='ViT-L-14'
        self.device=device
        self.model,_,self.preprocess=open_clip.create_model_and_transforms(self.architecture,pretrained=str(weights),device=device)
        self.model.eval()
        self.tokenizer=open_clip.get_tokenizer(self.architecture)
    def encode(self,image):
        import torch
        with torch.inference_mode():
            return torch.nn.functional.normalize(self.model.encode_image(self.preprocess(image.convert('RGB')).unsqueeze(0).to(self.device)).float(),dim=-1)
    def texts(self,texts):
        import torch
        with torch.inference_mode():
            return torch.nn.functional.normalize(self.model.encode_text(self.tokenizer(texts).to(self.device)).float(),dim=-1)

class VisualEvaluator:
    def __init__(self,encoder,aesthetic=None,reference=None):
        self.encoder=encoder
        self.aesthetic=aesthetic
        self.labels=list(PROMPTS)
        self.text_features=encoder.texts(list(PROMPTS.values()))
        self.reference=encoder.encode(reference) if reference is not None else None
    def __call__(self,path,query):
        import torch
        with Image.open(path) as source:
            if source.width*source.height>25000000: raise ValueError('PIXEL_LIMIT')
            image=source.convert('RGB')
        embedding=self.encoder.encode(image)
        with torch.inference_mode():
            logits=(embedding @ self.text_features.T).flatten()
            best=int(logits.argmax().item())
            similarity=float((embedding @ self.reference.T).item()) if self.reference is not None else None
        aesthetic=self.aesthetic.evaluate(image) if self.aesthetic is not None else None
        return {'category':self.labels[best],'classification_cosine':float(logits[best].item()),'similarity_normalized':None if similarity is None else max(0,min(1,(similarity+1)/2)),'similarity_cosine':similarity,'aesthetic_normalized':aesthetic['score'] if aesthetic else None,'aesthetic_evidence':aesthetic,'identity_status':'INSUFFICIENT_EVIDENCE','verified':False}
