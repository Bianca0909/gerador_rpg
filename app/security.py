from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from .schemas import TokenData

# Configurações de segurança
CHAVE_SECRETA = "your-secret-key-keep-it-secret"  # Em produção, use variável de ambiente
ALGORITMO = "HS256"
TEMPO_EXPIRACAO_TOKEN_MINUTOS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_password(password_texto: str, password_hash: str) -> bool:
    return pwd_context.verify(password_texto, password_hash)

def gerar_hash_password(password: str) -> str:
    return pwd_context.hash(password)

def criar_token_acesso(dados: dict, tempo_expiracao: Optional[timedelta] = None) -> str:
    dados_codificar = dados.copy()
    if tempo_expiracao:
        expira = datetime.utcnow() + tempo_expiracao
    else:
        expira = datetime.utcnow() + timedelta(minutes=15)
    dados_codificar.update({"exp": expira})
    token_jwt = jwt.encode(dados_codificar, CHAVE_SECRETA, algorithm=ALGORITMO)
    return token_jwt

def verificar_token(token: str, erro_credenciais) -> TokenData:
    try:
        payload = jwt.decode(token, CHAVE_SECRETA, algorithms=[ALGORITMO])
        username: str = payload.get("sub")
        if username is None:
            raise erro_credenciais
        dados_token = TokenData(username=username)
        return dados_token
    except JWTError:
        raise erro_credenciais
