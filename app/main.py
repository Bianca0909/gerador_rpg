from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, schemas, security
from .database import engine, get_db
from typing import List
from datetime import timedelta

# Criar as tabelas no banco de dados
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Simulador de Inventário de RPG")

# Configuração do CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins="http://localhost:3000",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="entrar")

# Função auxiliar para obter o usuário atual
async def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credenciais_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = security.verify_token(token, credenciais_exception)
    usuario = db.query(models.Usuario).filter(models.Usuario.nome_usuario == token_data.nome_usuario).first()
    if usuario is None:
        raise credenciais_exception
    return usuario

# Rotas públicas
@app.get("/")
def read_root():
    return {
        "message": "Bem-vindo ao Simulador de Inventário de RPG",
        "version": "1.0",
        "description": "API para gerenciamento de personagens e itens de RPG"
    }

@app.get("/exemplos")
def get_examples():
    return {
        "personagens": [
            {
                "nome": "Aragorn",
                "classe": "Guerreiro",
                "nivel": 10,
                "itens": [
                    {"nome": "Andúril", "tipo": "arma", "descricao": "Espada lendária reforjada"},
                    {"nome": "Cota de Malha", "tipo": "armadura", "descricao": "Armadura élfica resistente"}
                ]
            },
            {
                "nome": "Gandalf",
                "classe": "Mago",
                "nivel": 20,
                "itens": [
                    {"nome": "Glamdring", "tipo": "arma", "descricao": "Espada élfica antiga"},
                    {"nome": "Cajado", "tipo": "arma", "descricao": "Cajado mágico poderoso"}
                ]
            }
        ]
    }

# Autenticação
@app.post("/registrar", response_model=schemas.Usuario)
def registrar_usuario(usuario: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    db_usuario = db.query(models.Usuario).filter(models.Usuario.nome_usuario == usuario.nome_usuario).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Nome de usuário já registrado")
    
    db_usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    senha_hash = security.gerar_hash_senha(usuario.senha)
    db_usuario = models.Usuario(
        nome_usuario=usuario.nome_usuario,
        email=usuario.email,
        senha_hash=senha_hash
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@app.post("/login", response_model=schemas.Token)
async def entrar(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.nome_usuario == form_data.username).first()
    if not usuario or not security.verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    tempo_expiracao = timedelta(minutes=security.TEMPO_EXPIRACAO_TOKEN_MINUTOS)
    token_acesso = security.criar_token_acesso(
        dados={"sub": usuario.nome_usuario}, tempo_expiracao=tempo_expiracao
    )
    return {"access_token": token_acesso, "token_type": "bearer"}

# Rotas protegidas
@app.get("/meu-perfil", response_model=schemas.Usuario)
async def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual)):
    return usuario_atual

@app.get("/personagens", response_model=List[schemas.Personagem])
def listar_personagens(usuario_atual: models.Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    return db.query(models.Personagem).filter(models.Personagem.usuario_id == usuario_atual.id).all()

@app.post("/personagens", response_model=schemas.Personagem)
def criar_personagem(
    personagem: schemas.PersonagemCriar,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    db_personagem = models.Personagem(**personagem.dict(), usuario_id=usuario_atual.id)
    db.add(db_personagem)
    db.commit()
    db.refresh(db_personagem)
    return db_personagem

@app.get("/personagens/{personagem_id}/inventario", response_model=List[schemas.Item])
def obter_inventario(
    personagem_id: int,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    personagem = db.query(models.Personagem).filter(
        models.Personagem.id == personagem_id,
        models.Personagem.usuario_id == usuario_atual.id
    ).first()
    if not personagem:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return personagem.itens

@app.post("/personagens/{personagem_id}/inventario", response_model=schemas.Item)
def adicionar_item(
    personagem_id: int,
    item: schemas.ItemCriar,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    personagem = db.query(models.Personagem).filter(
        models.Personagem.id == personagem_id,
        models.Personagem.usuario_id == usuario_atual.id
    ).first()
    if not personagem:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    
    db_item = models.Item(**item.dict(), personagem_id=personagem_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/personagens/{personagem_id}/inventario/{item_id}", response_model=schemas.Item)
def atualizar_item(
    personagem_id: int,
    item_id: int,
    item: schemas.ItemCriar,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    db_item = db.query(models.Item).join(models.Personagem).filter(
        models.Item.id == item_id,
        models.Personagem.id == personagem_id,
        models.Personagem.usuario_id == usuario_atual.id
    ).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    
    for key, value in item.dict().items():
        setattr(db_item, key, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/personagens/{personagem_id}/inventario/{item_id}")
def deletar_item(
    personagem_id: int,
    item_id: int,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    db_item = db.query(models.Item).join(models.Personagem).filter(
        models.Item.id == item_id,
        models.Personagem.id == personagem_id,
        models.Personagem.usuario_id == usuario_atual.id
    ).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    
    db.delete(db_item)
    db.commit()
    return {"mensagem": "Item deletado com sucesso"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
