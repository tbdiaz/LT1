using UnityEngine;

// Selector del caso activo (requisito P1L4). Los casos se toman EXCLUSIVAMENTE
// de combinedRoot.results.cases del JSON exportado (G, Q, EX, EY, COMBO_R):
// no se ofrece ningun caso que no exista en la superposicion modelada.
// Al cambiar de caso, ModelLoader.SetActiveCase re-parsea forces /
// displacements / reactions / equilibrio y dispara ModelLoader.CaseChanged
// para que la deformada y los diagramas se refresquen.
public class CaseSelector : MonoBehaviour
{
    private ModelLoader loader;
    private string[] cases = new string[0];

    void Start()
    {
        loader = FindObjectOfType<ModelLoader>();
    }

    void LateUpdate()
    {
        if (loader == null) loader = FindObjectOfType<ModelLoader>();
        if (loader != null && cases.Length == 0)
            cases = loader.CaseList;
    }

    void OnGUI()
    {
        return; // selector horizontal en ViewerHUD
#pragma warning disable CS0162
        if (loader == null || loader.combinedRoot == null) return;
        if (cases == null || cases.Length == 0) return;

        float pw = 210f;
        float y = 240f;

        GUI.Box(new Rect(Screen.width - pw - 10f, y, pw, 40 + cases.Length * 24f),
                "Caso activo");

        GUILayout.BeginArea(new Rect(Screen.width - pw, y + 24, pw - 10, 60 + cases.Length * 22f));

        foreach (string c in cases)
        {
            GUIStyle btn = new GUIStyle(GUI.skin.button);
            if (c == loader.activeCase)
            {
                btn.normal.textColor = Color.white;
                btn.normal.background = Texture2D.blackTexture;
            }
            if (GUILayout.Button(c, btn))
            {
                if (c != loader.activeCase)
                    loader.SetActiveCase(c);
            }
        }

        GUIStyle grey = new GUIStyle(GUI.skin.label)
        {
            richText = true, fontSize = 9, wordWrap = true
        };
        var info = loader.GetCaseInfo(loader.activeCase);
        if (info != null && !string.IsNullOrEmpty(info.descripcion))
            GUILayout.Label($"<color=grey>{info.descripcion}</color>", grey);
        if (loader.activeCase == "COMBO_R" && info != null && info.coef != null)
            GUILayout.Label($"<color=grey>R = {info.coef.G:0.#}G + {info.coef.Q:0.#}Q "
                + $" + {info.coef.EX:0.#}EX + {info.coef.EY:0.#}EY</color>", grey);

        GUILayout.EndArea();
#pragma warning restore CS0162
    }
}
