# Cambio en API: Campo `bolsa_nombre` en Actividad Reciente

**Fecha:** 19 de marzo de 2026  
**Endpoints afectados:**
- `GET /dashboard/actividad-reciente`
- `GET /actividad`

---

## Resumen

Se agregó el campo **`bolsa_nombre`** a todos los eventos de tipo `"cambio_estado"` en los endpoints de actividad reciente. Este campo indica el nombre de la bolsa a la que pertenece el estado al que fue movido el alumno.

---

## Respuesta anterior (evento `cambio_estado`)

```json
{
  "tipo": "cambio_estado",
  "fecha": "2026-03-19T14:30:00",
  "id_referencia": "uuid-del-historial",
  "alumno": {
    "id_alumno": "uuid-del-alumno",
    "nombre": "Juan",
    "apellido": "Pérez"
  },
  "estado_nombre": "Contactado",
  "comentario": "Se realizó primer contacto",
  "autor": {
    "id_persona": "uuid-del-autor",
    "nombre": "María",
    "apellido": "López"
  }
}
```

## Respuesta nueva (evento `cambio_estado`)

```json
{
  "tipo": "cambio_estado",
  "fecha": "2026-03-19T14:30:00",
  "id_referencia": "uuid-del-historial",
  "alumno": {
    "id_alumno": "uuid-del-alumno",
    "nombre": "Juan",
    "apellido": "Pérez"
  },
  "estado_nombre": "Contactado",
  "bolsa_nombre": "Seguimiento",
  "comentario": "Se realizó primer contacto",
  "autor": {
    "id_persona": "uuid-del-autor",
    "nombre": "María",
    "apellido": "López"
  }
}
```

### Campo nuevo

| Campo          | Tipo              | Descripción                                                                 |
|----------------|-------------------|-----------------------------------------------------------------------------|
| `bolsa_nombre` | `string \| null`  | Nombre de la bolsa a la que pertenece el estado. `null` si el estado no tiene bolsa asignada. |

---

## Eventos de tipo `observacion` — Sin cambios

Los eventos de tipo `"observacion"` **no fueron modificados**. Su estructura sigue siendo la misma:

```json
{
  "tipo": "observacion",
  "fecha": "2026-03-19T15:00:00",
  "id_referencia": "uuid-de-la-observacion",
  "alumno": {
    "id_alumno": "uuid-del-alumno",
    "nombre": "Juan",
    "apellido": "Pérez"
  },
  "texto": "Contenido de la observación",
  "autor": {
    "id_persona": "uuid-del-autor",
    "nombre": "María",
    "apellido": "López"
  }
}
```

---

## Guía de integración en el Frontend

### 1. Actualizar el tipo/interfaz de TypeScript

```ts
// Agregar bolsa_nombre al tipo de evento de cambio de estado
interface EventoCambioEstado {
  tipo: "cambio_estado";
  fecha: string;
  id_referencia: string;
  alumno: {
    id_alumno: string;
    nombre: string | null;
    apellido: string | null;
  };
  estado_nombre: string | null;
  bolsa_nombre: string | null;   // <-- NUEVO
  comentario: string | null;
  autor: {
    id_persona: string | null;
    nombre: string | null;
    apellido: string | null;
  };
}
```

### 2. Mostrar en el componente de actividad reciente

En el componente que renderiza cada evento de `cambio_estado`, agregar el nombre de la bolsa. Ejemplo sugerido:

```tsx
{evento.tipo === "cambio_estado" && (
  <div className="evento-cambio-estado">
    <p>
      <strong>{evento.alumno.nombre} {evento.alumno.apellido}</strong>
      {" fue movido a "}
      <span className="estado">{evento.estado_nombre}</span>
      {evento.bolsa_nombre && (
        <span className="bolsa"> en bolsa <strong>{evento.bolsa_nombre}</strong></span>
      )}
    </p>
    {evento.comentario && <p className="comentario">{evento.comentario}</p>}
    <small>Por {evento.autor.nombre} {evento.autor.apellido} — {evento.fecha}</small>
  </div>
)}
```

### 3. Ejemplo de texto renderizado

**Antes:**
> **Juan Pérez** fue movido a **Contactado**

**Después:**
> **Juan Pérez** fue movido a **Contactado** en bolsa **Seguimiento**

### 4. Consideraciones

- `bolsa_nombre` puede ser `null` si el estado no tiene una bolsa asignada. En ese caso, simplemente no mostrar la sección de bolsa.
- El campo está disponible en **ambos endpoints** (`/dashboard/actividad-reciente` y `/actividad`), así que el cambio aplica sin importar cuál se consuma.
- No se requiere enviar ningún parámetro nuevo en el request; el campo viene incluido automáticamente en cada evento de tipo `cambio_estado`.
