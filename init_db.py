from database import initialize_database


if __name__ == "__main__":
    seeded = initialize_database(seed=True)
    if seeded:
        print("Banco de dados inicializado com dados de exemplo.")
    else:
        print("Banco de dados inicializado ou migrado com sucesso.")
