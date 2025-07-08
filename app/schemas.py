from pydantic import BaseModel, EmailStr
from typing import Optional, List

class ItemBase(BaseModel):
    nome: str
    descricao: str
    tipo: str

class ItemCriar(ItemBase):
    pass

class Item(ItemBase):
    id: int
    personagem_id: int

    class Config:
        from_attributes = True

class PersonagemBase(BaseModel):
    nome: str
    classe: str
    nivel: int = 1

class PersonagemCriar(PersonagemBase):
    pass

class Personagem(PersonagemBase):
    id: int
    usuario_id: int
    itens: List[Item] = []

    class Config:
        from_attributes = True

class UsuarioBase(BaseModel):
    nome_usuario: str
    email: EmailStr

class UsuarioCriar(UsuarioBase):
    senha: str

class Usuario(UsuarioBase):
    id: int
    personagens: List[Personagem] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    nome_usuario: Optional[str] = None
