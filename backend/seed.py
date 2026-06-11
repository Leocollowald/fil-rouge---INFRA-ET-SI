"""
Script de seed — Y-Plaza
Génère des données de démonstration réalistes avec Faker.
Usage : python seed.py

Ce script crée :
  - 5 agences
  - 15 utilisateurs (clients, agents, 1 direction)
  - 40 biens immobiliers
  - 60 transactions sur 6 mois (statuts variés)
"""

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ajout du dossier backend au path Python
sys.path.insert(0, str(Path(__file__).parent))

from faker import Faker
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.agency import Agency
from app.models.property import Favorite, Property, PropertyStatus, PropertyType, TransactionType
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User, UserRole


fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)

# Données fixes pour rendre le seed déterministe et réaliste
VILLES = [
    ("Paris", "75001"), ("Lyon", "69001"), ("Bordeaux", "33000"),
    ("Nantes", "44000"), ("Toulouse", "31000"), ("Montpellier", "34000"),
    ("Strasbourg", "67000"), ("Nice", "06000"), ("Rennes", "35000"),
    ("Lille", "59000"),
]

TYPES_BIEN = [
    PropertyType.apartment, PropertyType.apartment, PropertyType.apartment,
    PropertyType.house, PropertyType.house,
    PropertyType.commercial, PropertyType.office, PropertyType.land,
]

TYPES_TX = [TransactionType.sale, TransactionType.sale, TransactionType.rental]


def create_agencies(db: Session) -> list[Agency]:
    agences = [
        Agency(name="Y-Plaza Paris Centre", city="Paris", address="12 rue de Rivoli", zip_code="75001", phone="01 23 45 67 89", email="paris@yplaza.fr"),
        Agency(name="Y-Plaza Lyon", city="Lyon", address="8 place Bellecour", zip_code="69002", phone="04 72 00 00 00", email="lyon@yplaza.fr"),
        Agency(name="Y-Plaza Bordeaux", city="Bordeaux", address="5 cours de l'Intendance", zip_code="33000", phone="05 56 00 00 00", email="bordeaux@yplaza.fr"),
        Agency(name="Y-Plaza Nantes", city="Nantes", address="2 place du Commerce", zip_code="44000", phone="02 40 00 00 00", email="nantes@yplaza.fr"),
        Agency(name="Y-Plaza Toulouse", city="Toulouse", address="3 place du Capitole", zip_code="31000", phone="05 61 00 00 00", email="toulouse@yplaza.fr"),
    ]
    for a in agences:
        db.add(a)
    db.flush()
    print(f"  ✓ {len(agences)} agences créées")
    return agences


def create_users(db: Session, agences: list[Agency]) -> dict:
    """Retourne un dict {'clients': [...], 'agents': [...], 'direction': user}"""
    users: dict = {"clients": [], "agents": [], "direction": None}

    # Compte direction
    direction = User(
        email="direction@yplaza.fr",
        hashed_password=hash_password("Direction2024!"),
        first_name="Sophie",
        last_name="Martin",
        role=UserRole.direction,
        phone="01 00 00 00 01",
        agency_id=agences[0].id,
    )
    db.add(direction)
    users["direction"] = direction

    # Agents (un par agence)
    for i, agence in enumerate(agences):
        agent = User(
            email=f"agent{i+1}@yplaza.fr",
            hashed_password=hash_password("Agent2024!"),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role=UserRole.commercial,
            phone=fake.phone_number()[:20],
            agency_id=agence.id,
        )
        db.add(agent)
        users["agents"].append(agent)

    # Clients
    for i in range(10):
        client = User(
            email=f"client{i+1}@example.fr",
            hashed_password=hash_password("Client2024!"),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role=UserRole.client,
            phone=fake.phone_number()[:20],
        )
        db.add(client)
        users["clients"].append(client)

    db.flush()
    print(f"  ✓ {1 + len(agences) + 10} utilisateurs créés")
    return users


def create_properties(db: Session, agences: list[Agency], agents: list[User]) -> list[Property]:
    props = []
    for _ in range(40):
        ville, zip_code = random.choice(VILLES)
        ptype = random.choice(TYPES_BIEN)
        tx_type = random.choice(TYPES_TX)

        # Prix réalistes selon le type et la transaction
        if tx_type == TransactionType.rental:
            price = random.randint(500, 3000)
        elif ptype in (PropertyType.land, PropertyType.commercial):
            price = random.randint(50_000, 500_000)
        else:
            price = random.randint(80_000, 900_000)

        surface = random.randint(20, 300) if ptype != PropertyType.land else random.randint(200, 2000)
        rooms = random.randint(1, 6) if ptype in (PropertyType.apartment, PropertyType.house) else None
        bedrooms = random.randint(0, rooms - 1) if rooms and rooms > 1 else None

        # Statut varié pour les rapports
        status_weights = [0.5, 0.2, 0.2, 0.1]
        status = random.choices(
            [PropertyStatus.available, PropertyStatus.under_offer, PropertyStatus.sold, PropertyStatus.rented],
            weights=status_weights,
        )[0]

        agence = random.choice(agences)
        agent = random.choice(agents)

        # Dates réparties sur 6 mois
        days_ago = random.randint(1, 180)
        created = datetime.now(timezone.utc) - timedelta(days=days_ago)

        prop = Property(
            title=f"{ptype.value.capitalize()} {fake.street_address()}",
            description=fake.paragraph(nb_sentences=3),
            price=price,
            surface=float(surface),
            rooms=rooms,
            bedrooms=bedrooms,
            bathrooms=random.randint(1, 3) if rooms else None,
            property_type=ptype,
            transaction_type=tx_type,
            status=status,
            city=ville,
            address=fake.street_address(),
            zip_code=zip_code,
            latitude=float(fake.latitude()),
            longitude=float(fake.longitude()),
            agency_id=agence.id,
            agent_id=agent.id,
            created_at=created,
            updated_at=created,
        )
        db.add(prop)
        props.append(prop)

    db.flush()
    print(f"  ✓ {len(props)} biens créés")
    return props


def create_transactions(db: Session, props: list[Property], clients: list[User]) -> None:
    tx_count = 0
    # Sélectionne des biens pour y associer des transactions
    biens_avec_tx = random.sample(props, min(30, len(props)))

    for prop in biens_avec_tx:
        nb_tx = random.randint(1, 3)
        clients_shuffled = random.sample(clients, min(nb_tx, len(clients)))

        for idx, client in enumerate(clients_shuffled):
            # Statut cohérent avec le statut du bien
            if prop.status == PropertyStatus.sold and idx == 0:
                status = TransactionStatus.completed
            elif prop.status == PropertyStatus.rented and idx == 0:
                status = TransactionStatus.completed
            elif prop.status == PropertyStatus.under_offer and idx == 0:
                status = TransactionStatus.accepted
            else:
                status = random.choice([
                    TransactionStatus.pending,
                    TransactionStatus.pending,
                    TransactionStatus.rejected,
                ])

            days_ago = random.randint(0, 90)
            created = datetime.now(timezone.utc) - timedelta(days=days_ago)

            # Prix offert légèrement inférieur au prix affiché
            offered = float(prop.price) * random.uniform(0.85, 1.05)

            tx = Transaction(
                property_id=prop.id,
                buyer_id=client.id,
                agent_id=prop.agent_id,
                offered_price=round(offered, 2),
                status=status,
                notes=fake.sentence() if random.random() > 0.5 else None,
                created_at=created,
                updated_at=created + timedelta(days=random.randint(0, 10)),
            )
            db.add(tx)
            tx_count += 1

    db.flush()
    print(f"  ✓ {tx_count} transactions créées")


def create_favorites(db: Session, props: list[Property], clients: list[User]) -> None:
    fav_count = 0
    for client in clients:
        nb_favs = random.randint(0, 8)
        favs = random.sample(props, min(nb_favs, len(props)))
        for prop in favs:
            fav = Favorite(user_id=client.id, property_id=prop.id)
            db.add(fav)
            fav_count += 1
    db.flush()
    print(f"  ✓ {fav_count} favoris créés")


def run():
    db: Session = SessionLocal()
    try:
        # Vérification : ne pas ré-écraser si la DB a déjà des données
        existing = db.query(Agency).count()
        if existing > 0:
            print("⚠  La base contient déjà des données. Supprimez-les manuellement ou relancez sur une DB vierge.")
            return

        print("Création des données de démonstration…")
        agences = create_agencies(db)
        users = create_users(db, agences)
        props = create_properties(db, agences, users["agents"])
        create_transactions(db, props, users["clients"])
        create_favorites(db, props, users["clients"])
        db.commit()
        print("\n✅ Seed terminé avec succès !")
        print("\nComptes créés :")
        print("  direction@yplaza.fr   / Direction2024!")
        print("  agent1@yplaza.fr      / Agent2024!   (et agent2..5)")
        print("  client1@example.fr    / Client2024!  (et client2..10)")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur durant le seed : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
