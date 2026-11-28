"""Explicit operator model configuration; no downloads or silent fallback."""
class EditorRouter:
    def __init__(self,factories,preferred='flux'):
        if not factories or set(factories)-{'flux','qwen'} or preferred not in factories:
            raise ValueError('INVALID_EDITOR_CONFIGURATION')
        self.factories=dict(factories)
        self.preferred=preferred
        self.active=None
        self.editor=None
    def select(self,backend=None):
        name=backend or self.preferred
        if name not in self.factories: raise RuntimeError('EDITOR_NOT_CONFIGURED')
        if self.active!=name:
            if self.editor is not None:
                raise RuntimeError('MODEL_SWITCH_REQUIRES_WORKER_RESTART')
            editor=self.factories[name]()
            self.editor=editor
            self.active=name
        return self.editor
    def edit(self,image,prompt,seed=42):
        return self.select().edit(image,prompt,seed)
    def background(self,prompt,width=768,height=768,seed=42):
        return self.select('flux').background(prompt,width,height,seed)
