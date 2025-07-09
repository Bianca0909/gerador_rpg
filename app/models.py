from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    
    personagens = relationship("Personagem", back_populates="dono")

class Personagem(Base):
    __tablename__ = "personagens"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    classe = Column(String)
    nivel = Column(Integer, default=1)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    
    dono = relationship("Usuario", back_populates="personagens")
    itens = relationship("Item", back_populates="personagem")

class Item(Base):
    __tablename__ = "itens"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    descricao = Column(String)
    tipo = Column(String)  # arma, armadura, poção, etc
    personagem_id = Column(Integer, ForeignKey("personagens.id"))
    
    personagem = relationship("Personagem", back_populates="itens")
