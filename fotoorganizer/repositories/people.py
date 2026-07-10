"""Pessoas conhecidas: cadastro local, embeddings cifrados e associação
manual de rostos. Nada aqui identifica ninguém automaticamente — o estado
CONFIRMADO só nasce de ação explícita do usuário."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from fotoorganizer.models import (
    FaceEmbedding,
    FaceOccurrence,
    FaceState,
    Person,
)
from fotoorganizer.security.crypto import EmbeddingCipher


class PeopleRepository:
    def __init__(self, session_factory: sessionmaker[Session],
                 cipher: EmbeddingCipher) -> None:
        self._factory = session_factory
        self._cipher = cipher

    # -- pessoas -----------------------------------------------------------
    def criar_pessoa(self, nome: str, relacao: str | None = None) -> int:
        with self._factory() as session:
            pessoa = Person(nome=nome, relacao=relacao)
            session.add(pessoa)
            session.commit()
            return pessoa.id

    def listar_pessoas(self) -> list[Person]:
        with self._factory() as session:
            return list(session.scalars(select(Person).order_by(Person.nome)))

    def apagar_pessoa(self, person_id: int) -> None:
        """Remove a pessoa E TODOS os vestígios: embeddings (cascade) e
        ocorrências de rosto associadas — direito de apagar completo."""
        with self._factory() as session:
            session.execute(delete(FaceOccurrence).where(
                FaceOccurrence.person_id == person_id
            ))
            pessoa = session.get(Person, person_id)
            if pessoa is not None:
                session.delete(pessoa)  # cascade apaga face_embeddings
            session.commit()

    # -- embeddings (fotos de referência) -----------------------------------
    def adicionar_embedding(self, person_id: int, vetor: list[float],
                            modelo: str) -> int:
        with self._factory() as session:
            embedding = FaceEmbedding(
                person_id=person_id,
                blob_criptografado=self._cipher.cifrar(vetor),
                modelo=modelo,
            )
            session.add(embedding)
            session.commit()
            return embedding.id

    def embeddings_de(self, person_id: int) -> list[list[float]]:
        with self._factory() as session:
            blobs = session.scalars(
                select(FaceEmbedding.blob_criptografado).where(
                    FaceEmbedding.person_id == person_id
                )
            )
            return [self._cipher.decifrar(blob) for blob in blobs]

    # -- ocorrências de rosto -------------------------------------------------
    def registrar_deteccao(self, media_id: int,
                           bbox: dict | None = None) -> int:
        with self._factory() as session:
            occ = FaceOccurrence(media_id=media_id, bbox=bbox,
                                 estado=FaceState.DETECTADO)
            session.add(occ)
            session.commit()
            return occ.id

    def associar_manual(self, occurrence_id: int, person_id: int) -> None:
        """Associação manual = confirmação humana direta."""
        self._set_estado(occurrence_id, person_id, FaceState.CONFIRMADO)

    def marcar_incorreto(self, occurrence_id: int) -> None:
        with self._factory() as session:
            occ = session.get(FaceOccurrence, occurrence_id)
            if occ is not None:
                occ.estado = FaceState.INCORRETO
                occ.person_id = None
            session.commit()

    def _set_estado(self, occurrence_id: int, person_id: int | None,
                    estado: FaceState) -> None:
        with self._factory() as session:
            occ = session.get(FaceOccurrence, occurrence_id)
            if occ is not None:
                occ.person_id = person_id
                occ.estado = estado
            session.commit()

    def ocorrencias_confirmadas(self, media_id: int) -> list[tuple[int, str]]:
        """[(person_id, nome)] confirmados para uma foto — base da futura
        categoria 'família' (exige relacao='familiar' + confirmação)."""
        with self._factory() as session:
            stmt = (
                select(Person.id, Person.nome)
                .join(FaceOccurrence, FaceOccurrence.person_id == Person.id)
                .where(FaceOccurrence.media_id == media_id,
                       FaceOccurrence.estado == FaceState.CONFIRMADO)
            )
            return [tuple(linha) for linha in session.execute(stmt)]
