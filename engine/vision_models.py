"""Optional local inference adapters. Missing models fail explicitly."""
class BarcodeReader:
    def read(self,image):
        import zxingcpp
        from .identity import valid_gtin
        return [dict(text=x.text,format=str(x.format),valid_gtin=valid_gtin(x.text))
                for x in zxingcpp.read_barcodes(image)]

class OCRReader:
    def __init__(self, model):
        # Caller supplies initialized PaddleOCR 3.x instance and local weights.
        self.model=model
    def read(self,image):
        import numpy as np
        rows=[]
        for result in self.model.predict(np.asarray(image.convert('RGB'))):
            for text,score in zip(result['rec_texts'],result['rec_scores']):
                rows.append(dict(text=text,confidence=float(score)))
        return rows

class VisualEncoder:
    def __init__(self,weights,architecture='ViT-B-32',device='cpu'):
        from pathlib import Path
        if not Path(weights).is_file():
            raise FileNotFoundError('LOCAL_MODEL_WEIGHTS_REQUIRED')
        import open_clip
        self.model,_,self.preprocess=open_clip.create_model_and_transforms(architecture,pretrained=str(weights),device=device)
        self.model.eval()
        self.device=device

    def encode(self,image):
        import torch
        with torch.inference_mode():
            x=self.model.encode_image(self.preprocess(image.convert('RGB')).unsqueeze(0).to(self.device))
            return torch.nn.functional.normalize(x,dim=-1)

    def similarity(self,reference,candidate):
        return float((self.encode(reference)*self.encode(candidate)).sum().item())
