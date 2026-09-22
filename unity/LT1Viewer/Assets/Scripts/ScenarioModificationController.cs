using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

// Laboratorio de modificaciones del modelo. Mantiene los cambios separados
// del JSON y de los resultados OpenSees: una modificacion solo crea un
// escenario pendiente y nunca altera ni escala resultados ya calculados.
public class ScenarioModificationController : MonoBehaviour
{
    readonly Dictionary<string, float> loadFactors =
        new Dictionary<string, float>();
    readonly HashSet<int> inactiveElements = new HashSet<int>();

    ModelLoader loader;
    SelectionController selection;
    LoadVisualizationController loadVisualization;

    public string LoadFactorText = "1.00";
    public string Status { get; private set; } = "Escenario base sin modificaciones.";
    public bool RequiresReanalysis => loadFactors.Count > 0 || inactiveElements.Count > 0;
    public int InactiveElementCount => inactiveElements.Count;
    public int ModifiedLoadCaseCount => loadFactors.Count;

    public float CurrentLoadFactor
    {
        get
        {
            if (loader == null || string.IsNullOrEmpty(loader.activeCase)) return 1f;
            return loadFactors.TryGetValue(loader.activeCase, out float factor)
                ? factor : 1f;
        }
    }

    void Start()
    {
        FindControllers();
        SyncFactorText();
    }

    void OnEnable() { ModelLoader.CaseChanged += OnCaseChanged; }
    void OnDisable() { ModelLoader.CaseChanged -= OnCaseChanged; }

    void FindControllers()
    {
        loader = FindObjectOfType<ModelLoader>();
        selection = FindObjectOfType<SelectionController>();
        loadVisualization = FindObjectOfType<LoadVisualizationController>();
    }

    void OnCaseChanged(string caseKey)
    {
        SyncFactorText();
        if (loadVisualization != null && loadVisualization.Active)
            loadVisualization.Rebuild();
    }

    void SyncFactorText()
    {
        LoadFactorText = CurrentLoadFactor.ToString("0.###", CultureInfo.InvariantCulture);
    }

    public void ApplyLoadFactor()
    {
        if (loader == null) FindControllers();
        if (loader == null || string.IsNullOrEmpty(loader.activeCase))
        {
            Status = "No hay un caso de carga activo.";
            return;
        }

        string input = (LoadFactorText ?? "").Trim().Replace(',', '.');
        if (!float.TryParse(input, NumberStyles.Float, CultureInfo.InvariantCulture,
                            out float factor) || float.IsNaN(factor) ||
            float.IsInfinity(factor) || factor < 0f)
        {
            Status = "Factor invalido: use un numero mayor o igual que cero.";
            return;
        }

        if (Mathf.Abs(factor - 1f) <= 1e-6f)
            loadFactors.Remove(loader.activeCase);
        else
            loadFactors[loader.activeCase] = factor;

        LoadFactorText = factor.ToString("0.###", CultureInfo.InvariantCulture);
        Status = $"Intensidad {loader.activeCase} = {factor:0.###} x base.";
        if (loadVisualization == null) loadVisualization = FindObjectOfType<LoadVisualizationController>();
        if (loadVisualization != null && loadVisualization.Active)
            loadVisualization.Rebuild();
    }

    public bool IsElementActive(int tag) { return !inactiveElements.Contains(tag); }

    public void ToggleSelectedElement()
    {
        if (selection == null || loader == null) FindControllers();
        if (selection == null || selection.SelectedTag < 0)
        {
            Status = "Seleccione un elemento antes de cambiar su activacion.";
            return;
        }

        int tag = selection.SelectedTag;
        ElementRef reference = selection.GetElementRef();
        GameObject target = reference != null ? reference.gameObject : selection.SelectedObject;
        if (target == null)
        {
            Status = $"No se encontro el objeto del elemento {tag}.";
            return;
        }

        if (inactiveElements.Remove(tag))
        {
            target.SetActive(true);
            Status = $"Elemento {tag} reactivado.";
        }
        else
        {
            inactiveElements.Add(tag);
            target.SetActive(false);
            Status = $"Elemento {tag} desactivado en el escenario.";
        }
    }

    public void RestoreBaseScenario()
    {
        if (loader == null) FindControllers();
        if (loader != null)
        {
            foreach (int tag in inactiveElements)
                if (loader.elementRefs.TryGetValue(tag, out ElementRef reference) && reference != null)
                    reference.gameObject.SetActive(true);
        }
        inactiveElements.Clear();
        loadFactors.Clear();
        SyncFactorText();
        Status = "Escenario base restaurado; resultados originales vigentes.";
        if (loadVisualization != null && loadVisualization.Active)
            loadVisualization.Rebuild();
    }
}
