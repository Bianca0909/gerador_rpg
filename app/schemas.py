from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
import re

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
        orm_mode = True

class UsuarioBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

    @validator('username')
    def validate_username(cls, v):
        if not v.strip():
            raise ValueError('O nome de usuário não pode estar vazio')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('O nome de usuário deve conter apenas letras, números e _')
        return v

    @validator('email')
    def validate_email(cls, v):
        if not v.strip():
            raise ValueError('O email não pode estar vazio')
        return v

class UsuarioAtualizar(BaseModel):
    username: str
    email: EmailStr
    password: Optional[str] = None
    confirmar_password: Optional[str] = None

    @validator('password')
    def validate_password(cls, v, values):
        if v is not None:
            if len(v) < 8:
                raise ValueError('A senha deve ter pelo menos 8 caracteres')
            if not re.search(r'[A-Z]', v):
                raise ValueError('A senha deve conter pelo menos uma letra maiúscula')
            if not re.search(r'[a-z]', v):
                raise ValueError('A senha deve conter pelo menos uma letra minúscula')
            if not re.search(r'[0-9]', v):
                raise ValueError('A senha deve conter pelo menos um número')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
                raise ValueError('A senha deve conter pelo menos um caractere especial')
            if 'confirmar_password' in values and v != values['confirmar_password']:
                raise ValueError('As senhas não coincidem')
        return v

class UsuarioCriar(UsuarioBase):
    password: str = Field(..., min_length=8)
    confirmar_password: str

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('A senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('A senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('A senha deve conter pelo menos um número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('A senha deve conter pelo menos um caractere especial')
        return v

    @validator('confirmar_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('As senhas não coincidem')
        return v

class Usuario(UsuarioBase):
    id: int
    personagens: List[Personagem] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str
