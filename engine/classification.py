"""Zero-shot image categories are suggestions, not verified SKU or rights."""
LABELS = {
 'PACKSHOT':'a clean product packaging photograph on a plain background',
 'MARKETING':'a styled cosmetic product advertising photograph',
 'INGREDIENTS':'a close-up photograph of an ingredient list on packaging',
 'USAGE':'a photograph demonstrating application of a cosmetic product',
 'SWATCH':'a cosmetic color or texture swatch photograph',
 'LOGO':'a brand logo without a product',
 'OTHER':'an unrelated photograph or graphic'
}

class Classifier:
    def __init__(self,encoder):
        import open_clip
        import torch
        self.encoder=encoder
        tokenizer=open_clip.get_tokenizer(encoder.architecture)
        tokens=tokenizer(list(LABELS.values())).to(encoder.device)
        with torch.inference_mode():
            self.text=torch.nn.functional.normalize(encoder.model.encode_text(tokens),dim=-1)

    def classify(self,image):
        import torch
        with torch.inference_mode():
            scores=(self.encoder.encode(image) @ self.text.T).squeeze(0).cpu().tolist()
        ranked=sorted(zip(LABELS,scores),key=lambda x:x[1],reverse=True)
        return dict(category_suggestion=ranked[0][0],cosine_scores=dict(ranked),
                    margin=ranked[0][1]-ranked[1][1],status='NEEDS_MANUAL_REVIEW',
                    commercial_approved=False)
