import os
import shutil
import stat
import time

def remove_readonly(func, path, excinfo):
    """
    Manejador de errores para rmtree (shutil). 
    Si la excepción es un error de permiso, elimina el atributo de solo lectura e intenta de nuevo.
    """
    if func == os.rmdir: # No necesitamos intentar cambiar permisos en directorios vacíos
        return
        
    # Verificar si es un error de acceso denegado (WinError 5 o 13)
    if excinfo[0] is PermissionError or (hasattr(excinfo[1], 'winerror') and excinfo[1].winerror in (5, 13)):
        try:
            # 1. Eliminar el atributo de solo lectura (read-only)
            os.chmod(path, stat.S_IWRITE)
            
            # 2. Reintentar la función original (borrar archivo/carpeta)
            func(path)
        except Exception as e:
            # Si el reintento falla, devolvemos la excepción
            raise e
    else:
        # Si es otro tipo de error, lo devolvemos
        raise

def eliminar_subcarpetas_vacias(directorio_raiz):
    """
    Busca recursivamente y elimina todas las subcarpetas vacías.
    Usa un manejador de errores robusto para forzar la eliminación de archivos de solo lectura.
    """
    
    # Lista para almacenar las rutas de las carpetas eliminadas
    carpetas_eliminadas = []
    
    print(f"Iniciando limpieza de carpetas vacías en: {directorio_raiz}\n")

    # Recorrer el directorio de abajo hacia arriba (bottom-up)
    for raiz, dirs, archivos in os.walk(directorio_raiz, topdown=False):
        
        # Ignorar la carpeta raíz y las subcarpetas del entorno virtual (como venv\Include)
        if raiz == directorio_raiz or '\\venv\\' in raiz:
            continue
            
        # Comprobamos si la carpeta actual (raiz) está vacía
        if not os.listdir(raiz):
            try:
                # Intentar eliminar la carpeta vacía. shutil.rmtree usa rmdir para carpetas vacías.
                # No usamos el manejador de errores aquí, ya que la carpeta está vacía.
                os.rmdir(raiz) 
                carpetas_eliminadas.append(raiz)
                print(f"   -> ELIMINADA: {raiz}")
            except OSError as e:
                # Si falla, imprimimos el error y continuamos
                print(f"   ERROR: No se pudo eliminar la carpeta {raiz} (debería estar vacía). {e}")
        else:
            # La carpeta no está vacía, pero contiene archivos que impiden borrarla desde arriba.
            # Este es el caso cuando una carpeta superior está marcada como vacía pero Windows la bloquea.
            pass # Continuamos subiendo en el árbol

    # Segundo recorrido para eliminar las carpetas que contienen archivos bloqueados (solo lectura)
    # Volvemos a recorrer para asegurarnos de limpiar el resto de carpetas (Siglo, Dinastía, etc.)
    for raiz, dirs, archivos in os.walk(directorio_raiz, topdown=False):
        if raiz == directorio_raiz or '\\venv\\' in raiz:
            continue
            
        # Si la carpeta quedó vacía en el primer intento, o contiene solo archivos bloqueados:
        if not os.listdir(raiz):
            try:
                # Usamos shutil.rmtree con el manejador de errores remove_readonly
                shutil.rmtree(raiz, onerror=remove_readonly)
                if raiz not in carpetas_eliminadas:
                    carpetas_eliminadas.append(raiz + " [FORZADA]")
                    print(f"   -> ELIMINADA FORZADA: {raiz}")
            except Exception as e:
                # Manejar cualquier error residual que no se pudo resolver
                pass # Ignorar los errores finales de carpetas que realmente no se pueden eliminar (como venv\Include)


    if not carpetas_eliminadas:
        print("\nNo se encontraron subcarpetas vacías o bloqueadas para eliminar.")
    else:
        print(f"\nLimpieza completada. Total de carpetas eliminadas o forzadas: {len(carpetas_eliminadas)}")

# ----------------------------------------------------------------------
# Ejecución principal
# ----------------------------------------------------------------------

if __name__ == "__main__":
    directorio_actual = os.getcwd()
    
    # Nota: Ejecutar este script desde una Terminal con privilegios de Administrador sigue siendo vital.
    eliminar_subcarpetas_vacias(directorio_actual)