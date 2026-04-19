from database import USUARIOS_FIXOS, initialize_database


if __name__ == "__main__":
    seeded = initialize_database(seed=True)

    print("=" * 55)
    print("  SGDI — Banco de dados inicializado")
    print("=" * 55)

    if seeded:
        print("\n  Dados de exemplo inseridos com sucesso.\n")
    else:
        print("\n  Banco ja continha dados. Nenhum exemplo inserido.\n")

    print("  Usuarios disponíveis para login:")
    print("  " + "-" * 45)
    print(f"  {'Usuario':<20} {'Senha':<20}")
    print("  " + "-" * 45)
    for u in USUARIOS_FIXOS:
        print(f"  {u['username']:<20} {u['senha']:<20}")
    print("  " + "-" * 45)
    print("\n  Agora que o banco de dados está inicializado:\n")
    print("\n  Rode 'python app.py' para iniciar o servidor\n")
    print("\n  E acesse o aplicativo em: http://localhost:5000\n")
