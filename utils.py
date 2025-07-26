def eh_numero_romano(texto):
    """
    Verifica números romanos comuns em álbuns (I-XX)
    """
    if not texto:
        return False
    
    romanos = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                      'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX']
    
    return texto.upper() in romanos

def tratar_palavra_composta(palavra: str, separador: str, abrev: set) -> str:
    partes = palavra.split(separador)
    partes_proc = [
        parte.upper() if parte.upper() in abrev else parte.title()
        for parte in partes
    ]
    return separador.join(partes_proc)

def tratar(nome):
    """
    Processa nomes de álbuns com foco em música:
    - Números no início: mantém original (ex: "2pac" -> "2pac")
    - Números romanos: maiúsculo (ex: "vi" -> "VI")
    - Abreviações musicais: maiúsculo (ex: "ac/dc" -> "AC/DC")
    - Resto: title case
    """
    if not nome:
        return ""
    
    nome = nome.strip()
    
    # Se começar com número, mantém original
    if nome and nome[0].isdigit():
        return nome
    
    # Abreviações musicais comuns
    abrev = ['AC', 'DC', 'CD', 'DVD', 'LP', 'EP','BOX','CDS','DVDS']
    
    palavras = nome.split()
    resultado = []
    
    for i, palavra in enumerate(palavras):
        palavra = palavra.strip()
        
        # Número romano
        if eh_numero_romano(palavra):
            resultado.append(palavra.upper())
        
        # Começar com número
        elif palavra and palavra[0].isdigit():
            resultado.append(palavra)
        
        # Palavra com barra (AC/DC, CD/DVD)
        elif '/' in palavra:
            resultado.append(tratar_palavra_composta(palavra, '/', abrev))
            
        # Palavra com hífen (X-Men, Spider-Man)
        elif '-' in palavra:
            resultado.append(tratar_palavra_composta(palavra, '-', abrev))
            
        # Abreviações musicais
        elif palavra.upper() in abrev:
            resultado.append(palavra.upper())
        
        # Artigos/preposições no meio da frase
        elif i > 0 and palavra.lower() in ['the', 'of', 'and', 'in', 'on', 'at', 'to', 'for', 'with', 'from', 'vs','us']:
            resultado.append(palavra.lower())
        
        # Caso padrão
        else:
            resultado.append(palavra.title())
    
    return ' '.join(resultado)
