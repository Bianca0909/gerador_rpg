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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.post("/login", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not security.verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nome de usuário ou password incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Criar token de acesso
    access_token = security.criar_token_acesso(
        dados={"sub": usuario.username}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Função auxiliar para obter o usuário atual
async def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credenciais_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = security.verificar_token(token, credenciais_exception)
    usuario = db.query(models.Usuario).filter(models.Usuario.username == token_data.username).first()
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
@app.post("/register", response_model=schemas.Usuario)
def registrar_usuario(usuario: schemas.UsuarioCriar, db: Session = Depends(get_db)):
    db_usuario = db.query(models.Usuario).filter(models.Usuario.username == usuario.username).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Nome de usuário já registrado")
    
    db_usuario = db.query(models.Usuario).filter(models.Usuario.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="Email já registrado")
    
    password_hash = security.gerar_hash_password(usuario.password)
    db_usuario = models.Usuario(
        username=usuario.username,
        email=usuario.email,
        password_hash=password_hash
    )
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

# Rotas protegidas
@app.get("/meu-perfil", response_model=schemas.Usuario)
def ler_perfil(usuario_atual: models.Usuario = Depends(obter_usuario_atual)):
    return usuario_atual

@app.put("/meu-perfil", response_model=schemas.Usuario)
def atualizar_perfil(
    usuario_atualizado: schemas.UsuarioAtualizar,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    # Verifica se o username já está em uso por outro usuário
    usuario_existente = db.query(models.Usuario).filter(
        models.Usuario.username == usuario_atualizado.username,
        models.Usuario.id != usuario_atual.id
    ).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Username já está em uso")

    # Verifica se o email já está em uso por outro usuário
    usuario_existente = db.query(models.Usuario).filter(
        models.Usuario.email == usuario_atualizado.email,
        models.Usuario.id != usuario_atual.id
    ).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já está em uso")

    usuario_atual.username = usuario_atualizado.username
    usuario_atual.email = usuario_atualizado.email

    # Atualiza a senha apenas se uma nova senha foi fornecida
    if usuario_atualizado.password:
        usuario_atual.password_hash = security.get_password_hash(usuario_atualizado.password)

    try:
        db.commit()
        db.refresh(usuario_atual)
        return usuario_atual
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao atualizar perfil. Por favor, tente novamente."
        ) from e

@app.get("/personagens", response_model=List[schemas.Personagem])
def listar_personagens(usuario_atual: models.Usuario = Depends(obter_usuario_atual), db: Session = Depends(get_db)):
    try:
        print(f"Buscando personagens para usuário {usuario_atual.id}")
        personagens = db.query(models.Personagem).filter(models.Personagem.usuario_id == usuario_atual.id).all()
        print(f"Personagens encontrados: {personagens}")
        return personagens
    except Exception as e:
        print(f"Erro ao listar personagens: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar personagens: {str(e)}"
        )

@app.post("/personagens", response_model=schemas.Personagem)
def criar_personagem(
    personagem: schemas.PersonagemCriar,
    usuario_atual: models.Usuario = Depends(obter_usuario_atual),
    db: Session = Depends(get_db)
):
    try:
        if not personagem.nome or not personagem.classe:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nome e classe são obrigatórios"
            )

        # Verifica se já existe um personagem com o mesmo nome para este usuário
        existing_personagem = db.query(models.Personagem).filter(
            models.Personagem.nome == personagem.nome,
            models.Personagem.usuario_id == usuario_atual.id
        ).first()
        if existing_personagem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um personagem com este nome"
            )

        # Cria o personagem
        db_personagem = models.Personagem(**personagem.dict(), usuario_id=usuario_atual.id)
        db.add(db_personagem)
        db.commit()
        db.refresh(db_personagem)
        return db_personagem
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar personagem. Por favor, tente novamente."
        ) from e

@app.get("/personagens/{personagem_id}", response_model=schemas.Personagem)
def obter_personagem(
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
    return personagem

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
