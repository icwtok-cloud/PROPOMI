# R2 — upload de fotos de agencia

## Variables en Render (ya cargadas)

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_ENDPOINT`
- `R2_BUCKET` (ej. `propomi`)
- `R2_PUBLIC_BASE_URL` (ej. `https://pub-….r2.dev`)

## Endpoints

### `POST /properties/{property_id}/images`

- Auth: Bearer JWT de **agente** (`require_agent`)
- Agencia debe estar `VERIFIED` y ser dueña de la propiedad
- Multipart: campo **`files`** (uno o más archivos)
- Tipos: jpeg / png / webp, ≤ 3 MB c/u
- Máximo **5** fotos en total por propiedad (`MAX_PROPERTY_IMAGES`)

Ejemplo PowerShell (agente logueado):

```powershell
$token = "Bearer eyJ..."
$propId = "p-xxxxxxxxxxxx"
Invoke-RestMethod -Method Post `
  -Uri "https://propomi-api.onrender.com/properties/$propId/images" `
  -Headers @{ Authorization = $token } `
  -Form @{ files = Get-Item "C:\ruta\foto1.jpg" }
```

### `DELETE /properties/{property_id}/images?url=...`

Quita la URL del array y borra el objeto en R2 si pertenece a nuestro bucket.

## Crawler

No rehostea imágenes: sigue guardando URLs de los portales.
