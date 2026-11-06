export async function onRequestGet() {
  return Response.json({
    active_model: "Sangiang",
    models: ["Sangiang"],
  });
}

