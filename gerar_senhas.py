"""Uso local: python gerar_senhas.py (nunca cole senhas neste arquivo)."""
from getpass import getpass
from security import hash_password

for papel in ('Cliente (somente leitura)', 'Administrador (edição)'):
    while True:
        senha = getpass(f'Senha para {papel}, mínimo 12 caracteres: ')
        confirmar = getpass('Confirmar senha: ')
        if senha != confirmar:
            print('Senhas não conferem. Tente novamente.')
            continue
        try:
            print(hash_password(senha))
            break
        except ValueError as exc:
            print(exc)
