"""Local model inference adapter; classification and similarity are hypotheses."""
from pathlib import Path
from PIL import Image
from .aesthetic import AestheticPredictor

PROMPTS={
 'packshot':('a photograph of one complete cosmetic bottle or tube on a plain background','a retail product catalog photograph showing the entire labeled package','a studio photograph of a single skincare container with its label visible'),
 'lifestyle':('a photograph of a cosmetic product in a real bathroom or home setting','a person holding or applying a cosmetic product','a beauty product photographed in an everyday scene'),
 'advertising':('a designed beauty advertisement with promotional typography','a cosmetic campaign photograph with decorative props and dramatic lighting','a promotional social media graphic for a beauty product'),
 'detail':('a tightly cropped photograph of part of a cosmetic package','a close up of a product label or applicator','a macro photograph of a packaging detail'),
 'texture':('a macro photograph of uncontained cream smeared on a surface without packaging','a close up of bare liquid or gel texture without a bottle or tube','a photograph showing only cosmetic formula texture'),
 'swatch':('stripes of makeup pigment applied to skin','a photograph of multiple lipstick or eyeshadow color samples','cosmetic pigment swatches without retail packaging'),
 'group':('a photograph of several distinct cosmetic bottles or tubes together','a collection of multiple retail beauty products','a group photograph of several packaged cosmetics'),
 'logo':('a standalone brand logo on a blank background','a graphic containing only a company trademark','a brand wordmark without a product photograph'),
 'unrelated':('a photograph unrelated to beauty products','an ordinary scene without cosmetics','a non cosmetic object')
}
CLASSIFICATION_VERSION='prompt-ensemble-v2'

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
        import torch
        prompts=[p for label in self.labels for p in PROMPTS[label]]
        features=encoder.texts(prompts)
        self.text_features=torch.nn.functional.normalize(torch.stack([features[i*3:i*3+3].mean(dim=0) for i in range(len(self.labels))]),dim=-1)
        self.reference=encoder.encode(reference) if reference is not None else None
    def for_reference(self,path):
        from copy import copy
        from PIL import ImageOps
        bound=copy(self)
        with Image.open(path) as source:
            if source.width*source.height>25000000: raise ValueError('PIXEL_LIMIT')
            bound.reference=self.encoder.encode(ImageOps.exif_transpose(source).convert('RGB'))
        return bound
    def __call__(self,path,query):
        import torch
        with Image.open(path) as source:
            if source.width*source.height>25000000: raise ValueError('PIXEL_LIMIT')
            from PIL import ImageOps
            image=ImageOps.exif_transpose(source).convert('RGB')
        embedding=self.encoder.encode(image)
        with torch.inference_mode():
            logits=(embedding @ self.text_features.T).flatten()
            best=int(logits.argmax().item())
            top=logits.topk(2).values
            margin=float((top[0]-top[1]).item())
            similarity=float((embedding @ self.reference.T).item()) if self.reference is not None else None
        aesthetic=self.aesthetic.evaluate(image) if self.aesthetic is not None else None
        return {'category':self.labels[best] if margin>=.015 else 'unknown','classification_version':CLASSIFICATION_VERSION,'classification_margin':margin,'classification_scores':{label:float(logits[i].item()) for i,label in enumerate(self.labels)},'classification_cosine':float(logits[best].item()),'similarity_normalized':None if similarity is None else max(0,min(1,(similarity+1)/2)),'similarity_cosine':similarity,'aesthetic_normalized':aesthetic['score'] if aesthetic else None,'aesthetic_evidence':aesthetic,'identity_status':'INSUFFICIENT_EVIDENCE','verified':False}
