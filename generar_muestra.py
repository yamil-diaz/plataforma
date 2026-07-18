import os
import zipfile
import urllib.request
import pypdf

def crear_pdf_con_metadatos(filename, titulo, autor):
    # Crear un PDF simple con pypdf
    writer = pypdf.PdfWriter()
    # Añadimos un par de páginas en blanco
    page1 = writer.add_blank_page(width=595, height=842) # A4
    page2 = writer.add_blank_page(width=595, height=842)
    
    # Agregar metadatos
    metadata = {
        "/Title": titulo,
        "/Author": autor,
    }
    writer.add_metadata(metadata)
    
    with open(filename, "wb") as f:
        writer.write(f)
    print(f"✔ PDF creado: {filename}")

def generar_muestra():
    print("Iniciando generación de datos de muestra para importación...")
    
    # Crear carpeta temporal
    temp_dir = "muestra_zip"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Descargar imágenes reales de Unsplash para portadas
    urls = {
        "moby_dick.jpg": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
        "orgullo_y_prejuicio.png": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=400"
    }
    
    for filename, url in urls.items():
        try:
            path = os.path.join(temp_dir, filename)
            urllib.request.urlretrieve(url, path)
            print(f"✔ Portada descargada: {filename}")
        except Exception as e:
            print(f"⚠ No se pudo descargar la portada {filename} (usando imagen simulada): {e}")
            # Escribir archivo de imagen ficticio en caso de falta de conexión
            with open(os.path.join(temp_dir, filename), "wb") as f:
                f.write(b"ficticio")

    # Crear PDFs correspondientes
    crear_pdf_con_metadatos(
        os.path.join(temp_dir, "moby_dick.pdf"),
        "Moby Dick o La Ballena",
        "Herman Melville"
    )
    crear_pdf_con_metadatos(
        os.path.join(temp_dir, "orgullo_y_prejuicio.pdf"),
        "Orgullo y Prejuicio",
        "Jane Austen"
    )
    
    # Crear archivo ZIP
    zip_filename = "libros_prueba.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            zipf.write(file_path, file)
            
    print(f"\n★ ¡ÉXITO! Se ha creado el archivo '{zip_filename}' listo para probar la importación masiva.")
    
    # Limpiar carpeta temporal
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)

if __name__ == "__main__":
    generar_muestra()
