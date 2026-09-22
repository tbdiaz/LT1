using UnityEngine;

[RequireComponent(typeof(Camera))]
public class OrbitCamera : MonoBehaviour
{
    public Vector3 target = Vector3.zero;
    public float distance = 10f;
    public float minDistance = 0.5f;
    public float maxDistance = 200f;
    public float orbitSpeed = 3f;
    public float zoomSpeed = 5f;
    public float panSpeed = 0.5f;

    private Vector3 initialTarget;
    private float initialDistance;
    private bool isOrbiting;
    private bool isPanning;
    private Vector3 lastMousePosition;
    private float lastClickTime;

    void Start()
    {
        initialTarget = target;
        initialDistance = distance;
        UpdatePosition();
    }

    void Update()
    {
        if (Input.touchCount > 0)
        {
            HandleTouch();
            return;
        }
        HandleOrbit();
        HandlePan();
        HandleZoom();
        HandleReset();
    }

    void HandleTouch()
    {
        if (Input.touchCount == 1)
        {
            Touch touch = Input.GetTouch(0);
            if (ViewerHUD.PointerOverHud(touch.position) ||
                touch.phase != TouchPhase.Moved) return;

            Vector2 delta = touch.deltaPosition;
            float h = delta.x * orbitSpeed * 0.10f;
            float v = delta.y * orbitSpeed * 0.10f;
            Vector3 offset = transform.position - target;
            Quaternion rotH = Quaternion.AngleAxis(h, Vector3.up);
            Vector3 pitchAxis = Vector3.Cross(offset, Vector3.up).normalized;
            if (pitchAxis.sqrMagnitude < 1e-6f) pitchAxis = transform.right;
            offset = rotH * Quaternion.AngleAxis(v, pitchAxis) * offset;
            if (offset.sqrMagnitude > 0.001f)
            {
                transform.position = target + offset;
                transform.LookAt(target);
            }
            return;
        }

        Touch a = Input.GetTouch(0);
        Touch b = Input.GetTouch(1);
        if (ViewerHUD.PointerOverHud(a.position) ||
            ViewerHUD.PointerOverHud(b.position)) return;

        Vector2 previousA = a.position - a.deltaPosition;
        Vector2 previousB = b.position - b.deltaPosition;
        float previousDistance = Vector2.Distance(previousA, previousB);
        float currentDistance = Vector2.Distance(a.position, b.position);
        float pinch = currentDistance - previousDistance;
        distance = Mathf.Clamp(distance - pinch * distance * 0.0025f,
                               minDistance, maxDistance);

        Vector2 averageDelta = (a.deltaPosition + b.deltaPosition) * 0.5f;
        float scale = panSpeed * distance * 0.001f;
        Vector3 pan = transform.right * (-averageDelta.x * scale) +
                      transform.up * (-averageDelta.y * scale);
        target += pan;
        UpdatePosition();
    }

    void HandleOrbit()
    {
        if (Input.GetMouseButtonDown(1))
        {
            lastMousePosition = Input.mousePosition;
            isOrbiting = true;
        }
        if (Input.GetMouseButtonUp(1))
            isOrbiting = false;

        if (!isOrbiting) return;

        Vector3 delta = Input.mousePosition - lastMousePosition;
        float h = delta.x * orbitSpeed * 0.1f;
        float v = delta.y * orbitSpeed * 0.1f;

        Vector3 offset = transform.position - target;
        Quaternion rotH = Quaternion.AngleAxis(h, Vector3.up);
        Quaternion rotV = Quaternion.AngleAxis(v, Vector3.Cross(offset, Vector3.up).normalized);

        offset = rotH * rotV * offset;

        if (offset.sqrMagnitude > 0.001f)
        {
            transform.position = target + offset;
            transform.LookAt(target);
        }

        lastMousePosition = Input.mousePosition;
    }

    void HandlePan()
    {
        bool middleDown = Input.GetMouseButtonDown(2);
        bool altLeftDown = Input.GetKey(KeyCode.LeftAlt) && Input.GetMouseButtonDown(0);

        bool middleUp = Input.GetMouseButtonUp(2);
        bool altLeftUp = Input.GetKey(KeyCode.LeftAlt) && Input.GetMouseButtonUp(0);

        if (middleDown || altLeftDown)
        {
            lastMousePosition = Input.mousePosition;
            isPanning = true;
        }
        if (middleUp || altLeftUp)
            isPanning = false;

        if (!isPanning) return;

        Vector3 delta = Input.mousePosition - lastMousePosition;
        float panScale = panSpeed * distance * 0.001f;
        Vector3 pan = transform.right * (-delta.x * panScale) + transform.up * (-delta.y * panScale);
        target += pan;
        transform.position += pan;
        lastMousePosition = Input.mousePosition;
    }

    void HandleZoom()
    {
        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (Mathf.Abs(scroll) < 0.001f) return;

        distance -= scroll * zoomSpeed * distance * 0.2f;
        distance = Mathf.Clamp(distance, minDistance, maxDistance);
        UpdatePosition();
    }

    void HandleReset()
    {
        if (Input.GetKeyDown(KeyCode.R))
        {
            ResetCamera();
            return;
        }

        if (Input.GetMouseButtonDown(0) && !Input.GetKey(KeyCode.LeftAlt))
        {
            float clickTime = Time.time;
            if (clickTime - lastClickTime < 0.3f)
                ResetCamera();
            lastClickTime = clickTime;
        }
    }

    void ResetCamera()
    {
        target = initialTarget;
        distance = initialDistance;
        UpdatePosition();
    }

    void UpdatePosition()
    {
        Vector3 direction = transform.position - target;
        if (direction.sqrMagnitude < 0.001f)
            direction = -Vector3.forward;

        transform.position = target + direction.normalized * distance;
        transform.LookAt(target);
    }

    public void SetTarget(Vector3 newTarget)
    {
        target = newTarget;
        initialTarget = newTarget;
        UpdatePosition();
    }
}
