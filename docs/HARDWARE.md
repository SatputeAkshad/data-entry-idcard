# Windows hardware verification — required before production

No Nikon device or CorelDRAW installation has been physically tested in this development environment. The COM adapter is real Windows automation code, but its behavior, typography, effects, clipping, color output and PDF settings require validation on your installation. Do not treat passing simulation tests as hardware certification.

## Nikon discovery and setup

1. Connect the Nikon by USB, power it on, and record the exact camera model and firmware. Use an adequately charged battery or supported external power.
2. Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose.ps1` from the repository. The JSON reports Windows PnP device names, instance IDs and status. Discovery is not a claim of remote-control support.
3. Check the model and Windows version against Nikon's current supported-camera documentation. If compatible, install Nikon NX Tether or another licensed compatible tethering application yourself. ID Card Studio does not install proprietary software.
4. Close competing camera-control/download applications, including Nikon Transfer and Camera Control Pro if using NX Tether. The application cannot determine every camera-in-use condition from PnP alone; check the tethering application's status.
5. Set the camera/tethering software to save JPEG to a private folder, e.g. `%LOCALAPPDATA%\IDCardStudio\NikonIncoming`. RAW-only transfers are not supported. JPEG+RAW is acceptable; RAW is ignored.
6. Launch ID Card Studio. In Settings, enter that absolute folder path. The agent establishes a baseline; only new or changed image files are received afterward.
7. Register/open a student, click Capture Photo, and trigger the shutter on the body or in Nikon software. The button arms a five-minute reception session; it does not remotely click the shutter.
8. Wait for the thumbnail, select the matching image explicitly, inspect the face, crop/rotate/zoom if needed and Accept Photo. Retake creates a new capture ID; rejected captures cannot be approved.
9. Save & Next and confirm that the previous image is cleared. Shoot again. Do a deliberate delayed-transfer test: the old image must remain an unassigned inbox candidate, never automatically bind to the next student.
10. Disconnect/reconnect the USB cable. Diagnostics refresh about every 30 seconds. New valid files should still appear after reconnection.

If tethering is unsupported, use Import Photo. This shares the same image validation, approval, crop and storage workflow. Exact accepted source bytes are retained separately from the processed JPEG.

### Direct SDK status

`NikonSDKAdapter` deliberately advertises `remote_shutter=false`, `live_view=false`, and `receive_images=false`. It is an unavailable capability declaration, not an implemented camera driver. A real direct-control driver needs the exact model, Nikon's supported SDK package/license, and hardware testing. This cannot be completed by guessing an SDK ABI. Nikon's SDK information is at https://sdk.nikonimaging.com/information/en/ and its SDK downloads/licensing must be obtained through Nikon.

Official compatibility guidance:
- https://downloadcenter.nikonimglib.com/en/download/sw/278.html
- https://nikonimglib.com/nx_tether/onlinehelp/en/01_what_nx_tether_can_do_for_you_1.html

## CorelDRAW 21 diagnostic

Run after installation, with ID Card Studio stopped:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\diagnose.ps1 -CorelTest
```

This enumerates registered CorelDRAW application ProgIDs from both registry views, selects an actually registered version-specific `.21` entry, connects using pywin32's generated type-library wrapper, confirms `VersionMajor == 21`, reads installed enum constants, creates a test document, saves CDR, publishes PDF, reports the type-library identity, and closes only its own document. It does not call `Application.Quit`.

The diagnostic may open CorelDRAW visibly. Complete its first-run/licensing prompts beforehand. Test artifacts appear under the private data directory's `tmp\diagnostic` folder. No VBA macro is required by this implementation. Missing COM/type-library/automation components must be repaired with the original Corel installer. Never install arbitrary newer Corel libraries to satisfy this check.

If the call stalls, inspect CorelDRAW for dialogs. Job workers time out after 180 seconds without progress and pause the agent. The diagnostic itself should be run interactively and monitored. Do not kill a CorelDRAW session containing unsaved personal work.

### APIs checked against the 2019 documentation

- Image import: https://community.coreldraw.com/sdk/api/draw/21/m/layer.import
- Photo clipping: https://community.coreldraw.com/sdk/api/draw/21/m/shape.addtopowerclip
- PDF publishing: https://community.coreldraw.com/sdk/api/draw/21/m/document.publishtopdf

Additional property/method calls (`Text.Story.Text`, shape dimensions, `SetSize`, page traversal, `VersionMajor`, document save/close) must be verified against the installed v21 type library and Object Browser. Online pages for several properties were inaccessible during development; they are not being represented as individually verified against published v21 documentation.

## Prepare an existing design

1. Make a backup of your design. Use CorelDRAW 2019 to save a CDR compatible with version 21.
2. Set the page's physical size to the actual card size, e.g. 85.6 × 54 mm. If using 3 mm bleed, the page must be 91.6 × 60 mm with artwork extending to every edge; the application does not invent bleed.
3. For a two-sided card, use page 1 for front and page 2 for back, same physical dimensions. Separate back CDR uploads are not currently implemented; consolidate the pages in CorelDRAW first.
4. In the Objects docker, rename the actual text shapes, e.g. `STUDENT_NAME`, `STUDENT_ID`, `CLASS`, `BACK_STUDENT_ID`. Editing visible text does not rename its shape.
5. Use exactly one occurrence of each mapped object name across the document. Objects inside ordinary groups are traversed. Mapped placeholders inside existing PowerClips, symbols or master-layer constructs have not been validated and should be moved to ordinary editable layers.
6. For the photograph, create an empty, closed rectangle/curve named `STUDENT_PHOTO`. Remove existing contents from the frame before registration. Keep decorative borders as separate shapes. The approved photo is proportionally filled and centered into the frame using PowerClip.
7. Use uniform formatting within each replaceable text object. Mixed-run typography is not guaranteed to survive full-story replacement. Set desired fonts/alignment in the template. Make placeholders large enough for your longest expected value; expanded bounds and configured character limits cause a per-card error, not silent shrinking.
8. Install all required fonts on Windows. Open the template manually and resolve any font substitution/effect warnings. Automated detection of all missing fonts and unsupported effects is not implemented.
9. Configure appropriate CorelDRAW Publish to PDF settings for your printer, color management, font embedding and output quality. The adapter calls `PublishToPDF`; it does not assert PDF/X conformance or override every version-dependent PDF setting.

## Register and map

Open Templates, select the CDR, name it and enter card dimensions/bleed. Map internal object names to institution field keys. Map photo frames to `photo`. Multiple differently named objects can map to one field, including repeated front/back text. Uploading stores a private copy; production uses additional disposable working copies.

Click Inspect template and review Production's inspection report: pages, physical size, object names, counts and shape types. Fix missing/duplicated names in CorelDRAW and register a corrected template. Template revisions are separate registrations; existing production snapshots remain unchanged.

## First-card and batch acceptance

1. Create an institution and configure required/dropdown fields.
2. Register its template and run inspection.
3. Enter Student A, receive photo A1, retake, receive different photo A2, accept A2, save.
4. Save & Next: no Student A photograph should appear in the new registration.
5. Register Student B with photo B1 and save.
6. Select Student A in Student Records, choose template, Generate Cards.
7. Inspect the resulting CDR and PDF in Production. Compare every field and face with the approved record. Verify the original template is unchanged.
8. Generate A and B together; confirm both documents contain the correct individual name/photo. A previously rejected A1 must not appear anywhere in production.
9. Cause a recoverable failure (e.g. a template mapping typo), observe the per-student error, fix by registering a corrected template and submit a new job. Retry is for transient failures of the same snapshot; it does not pick up changed student/template data.
10. For transient failures, retry only after inspecting/closing abandoned job working documents. Successful entries are retained and skipped. Never automate simultaneous manual editing of a job's working document.
11. Arrange sheets, inspect front/back ordering, and print a single sheet at **Actual size / 100%**, without fit-to-page. Measure card and crop-mark positions with a ruler. Flip using the chosen long/short edge; check alignment against a light before a batch.

Record camera model, firmware, Nikon software version, Windows version, CorelDRAW build, type-library ID, fonts, PDF preset, printer/driver and measurement results in `docs/HARDWARE-RESULTS.md` locally. Do not mark the installation production-verified until this procedure passes.
