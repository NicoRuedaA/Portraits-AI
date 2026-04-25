import os

def contar_archivos_de_imagen(directorio_raiz):
    """
    Recorre recursivamente las subcarpetas de un directorio dado 
    y cuenta solo los archivos de imagen (.jpg, .jpeg, .png).
    Excluye:
    1. Archivos en el directorio raíz.
    2. Todo el contenido dentro de la carpeta 'venv' y '__pycache__'.
    """
    
    contador_archivos = 0
    # Lista de extensiones de archivos de imagen válidas
    EXTENSIONES_VALIDAS = ('.jpg', '.jpeg', '.png')
    # Lista de carpetas a excluir de la recursión (añade aquí otras carpetas de código si es necesario)
    CARPETAS_A_EXCLUIR = ['venv', '__pycache__', '.git'] 
    
    print(f"Iniciando conteo de retratos válidos en: {directorio_raiz}\n")

    # Recorrer el directorio de forma recursiva
    for raiz, subdirs, archivos in os.walk(directorio_raiz):
        
        # 1. Eliminar carpetas de exclusión de la lista de subdirectorios a visitar
        # Esto es la clave: evita que os.walk descienda a venv, __pycache__, etc.
        subdirs[:] = [d for d in subdirs if d.lower() not in CARPETAS_A_EXCLUIR]
        
        # 2. Ignorar el directorio raíz (donde están tus scripts .py)
        if raiz == directorio_raiz:
            print(f"Se ignoran {len(archivos)} archivos en el directorio raíz.")
            continue
        
        # 3. Contar solo archivos de imagen
        num_archivos_contados = 0
        
        for archivo in archivos:
            archivo_min = archivo.lower()
            
            # Criterio: Solo contar si tiene una extensión de imagen válida
            if archivo_min.endswith(EXTENSIONES_VALIDAS):
                num_archivos_contados += 1

        contador_archivos += num_archivos_contados
        
        # Opcional: Mostrar el conteo por carpeta (si es > 0)
        if num_archivos_contados > 0:
            print(f"   [+] Carpeta '{os.path.basename(raiz)}': {num_archivos_contados} retratos")

    return contador_archivos

# ----------------------------------------------------------------------
# Ejecución principal
# ----------------------------------------------------------------------

if __name__ == "__main__":
    directorio_actual = os.getcwd()
    
    # Intenta obtener el conteo de tu dataset
    total = contar_archivos_de_imagen(directorio_actual)
    
    print("\n-------------------------------------------")
    print(f"✅ ¡Conteo finalizado!")
    print(f"TOTAL DE RETRATOS LISTOS PARA LORA: {total}")
    print("-------------------------------------------")