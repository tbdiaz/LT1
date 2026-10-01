using System;

[Serializable]
public sealed class Semana06BeamData
{
    public int schemaVersion;
    public string sourceFile;
    public int elementTag;
    public Semana06Element element;
    public Semana06Node[] nodes;
    public Semana06Load[] loads;
    public Semana06ForceCase[] forceCases;
    public Semana06DisplacementCase[] displacementCases;
    public Semana06DiagramAvailability diagramAvailability;
    public Semana06DemandCapacity demandCapacity;
    public Semana06Units units;
}

[Serializable]
public sealed class Semana06Element
{
    public int elementTag;
    public string type;
    public string origin;
    public int nodeI;
    public int nodeJ;
    public float length_m;
    public string level;
    public string lt1Level;
    public int originalTag;
    public Semana06Section section;
}

[Serializable]
public sealed class Semana06Section
{
    public string label;
    public float area_m2;
    public float Iy_m4;
    public float Iz_m4;
    public float J_m4;
    public float E_kPa;
    public float G_kPa;
}

[Serializable]
public sealed class Semana06Node
{
    public int nodeTag;
    public float x;
    public float y;
    public float z;
    public string origin;
    public string level;
}

[Serializable]
public sealed class Semana06Load
{
    public string caseName;
    public string type;
    public float w_kN_m;
    public float total_kN;
    public float tributaryArea_m2;
    public bool hasTributaryArea;
}

[Serializable]
public sealed class Semana06ForceCase
{
    public string caseName;
    public float N1;
    public float Vy1;
    public float Vz1;
    public float T1;
    public float My1;
    public float Mz1;
    public float N2;
    public float Vy2;
    public float Vz2;
    public float T2;
    public float My2;
    public float Mz2;
}

[Serializable]
public sealed class Semana06DisplacementCase
{
    public string caseName;
    public float[] nodeI;
    public float[] nodeJ;
    public float translationMagnitudeI_m;
    public float translationMagnitudeJ_m;
}

[Serializable]
public sealed class Semana06DiagramAvailability
{
    public bool endForcesAvailable;
    public bool internalStationResultsAvailable;
    public string note;
}

[Serializable]
public sealed class Semana06DemandCapacity
{
    public bool available;
    public string note;
}

[Serializable]
public sealed class Semana06Units
{
    public string coordinates;
    public string force;
    public string moment;
    public string distributedLoad;
    public string displacement;
    public string rotation;
}
