# OTAN Imperial

Página de clasificación de la alianza OTAN para Goodgame Empire.

## Automatización

- `scripts/update_rankings.py` consulta la API pública de Empire Rankings, sin iniciar sesión en cuentas del juego.
- `.github/workflows/update-rankings.yml` solicita una actualización cada 15 minutos mediante GitHub Actions (GitHub puede retrasar u omitir ejecuciones programadas).
- `.github/workflows/deploy-pages.yml` publica el sitio en GitHub Pages cuando el repositorio tiene Pages configurado con **GitHub Actions**.
- Si la API no responde o una categoría no se puede recorrer completamente, se conserva la última captura verificada; no se inventan puntos.
- El servidor configurado es `EmpireEx_2` y los eventos iniciales son 40, 44 y 46. **Verificar que este identificador corresponda al servidor Internacional 2 y que los eventos sean los deseados antes de confiar en los resultados.**
- El filtro es el nombre exacto de alianza `OTAN` (sin distinguir mayúsculas).

## Activación y comprobación

1. En **Settings → Pages → Build and deployment**, seleccionar **GitHub Actions**. Si Pages ya está configurado, no es necesario cambiarlo.
2. En **Actions**, ejecutar manualmente **Update OTAN rankings** para probar la API.
3. Revisar el registro de ejecución: debe finalizar correctamente y generar `data/rankings.json` con fecha y jugadores reales. Si falla, no considerar el sistema operativo.
4. Confirmar que la clasificación corresponde al servidor y evento correctos.
5. Abrir `https://gabrielrosariobeato8.github.io/OTAN/` **solo después de que GitHub Pages informe un despliegue correcto**.

La frecuencia es solicitada cada 15 minutos, no garantizada al minuto. Las consultas completas pueden consumir tiempo y depender de límites de la API pública. El proyecto es independiente de Goodgame Studios.
