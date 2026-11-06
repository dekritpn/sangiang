export async function onRequestGet() {
  return Response.json({
    active_model: "Sangiang",
    available_models: [
      {
        name: "Sangiang",
        is_active: true,
        is_finetuned: true,
      },
    ],
  });
}

