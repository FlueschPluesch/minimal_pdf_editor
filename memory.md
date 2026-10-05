# Minimal PDF Editor - Memory

## Projektbeschreibung
Eine grafische Desktop-Anwendung (GUI) zum Bearbeiten von PDF-Dateien.

## Hauptfunktionen
1. **PDF Laden (Vertikales Scrollen):** Öffnen und Anzeigen aller PDF-Seiten fortlaufend untereinander.
2. **Zoom:** Zoom In (+), Zoom Out (-) und Reset Zoom in der Toolbar sowie Unterstützung für `STRG + Mausrad`. Die App merkt sich die letzte Zoom-Stufe.
3. **Text einfügen:** Hinzufügen von Text an beliebigen Stellen im PDF. Elemente sind durch Drag & Drop verschiebbar und in der Größe anpassbar. Zusätzlich gibt es eine Option zum Anpassen des **Letter Spacings (Zeichenabstands)**.
4. **Check/Cross Marks:** Einfügen von "X" (Kreuz) und "✓" (Haken) Symbolen zum Ausfüllen von Checkboxen. Beide Symbole werden dynamisch aus Linien gezeichnet.
5. **Mark Color:** Einstellbare Farbe für Formen, "X" und "✓" Symbole (Standard: Schwarz).
6. **Formen (Shapes):** Einfügen primitiver Formen wie Rechteck (⬛), Kreis (⭕) und Dreieck (🔺).
7. **Fill-Modus:** Ein Umschalter (🟩 Fill: ON/OFF), um festzulegen, ob neu gezeichnete Formen gefüllt (ausgemalt) oder nur als Umriss (Outline) gezeichnet werden sollen.
8. **Bilder einfügen:** Hinzufügen von Bildern in das PDF. Elemente sind frei verschiebbar und skalierbar.
9. **Unterschrift:** Hinterlegen einer Unterschrift als Bilddatei, welche gespeichert und einfach wiederverwendet (eingefügt) werden kann.
10. **Druckfunktion (Neu):** Ein Button (🖨️ Print PDF) mit Shortcut `STRG + P`, um den aktuellen Bearbeitungsstand direkt an das System-Druckmenü zu übergeben.
11. **Datum im Dateinamen (Neu):** Optionale Checkbox "Add date to filename" in den Einstellungen (standardmäßig aktiv). Wenn aktiviert, wird beim Speichern automatisch das aktuelle Datum im Format "dd_mm_yyyy" als Präfix vorangestellt, sofern nicht bereits ein Datum (im Format dd_mm_yyyy, dd-mm-yyyy, dd.mm.yyyy, dd/mm/yyyy oder 2-stelliger Jahreszahl/ohne Jahr) am Dateianfang erkannt wurde.

## Technologie-Stack (Vorschlag)
- **Sprache:** Python 3
- **GUI-Framework:** PyQt6 (für eine moderne und reaktionsschnelle Desktop-Oberfläche)
- **PDF-Verarbeitung:** PyMuPDF (fitz) - hervorragend geeignet zum Rendern von PDF-Seiten als Bilder für die Anzeige und zum nativen Einfügen von Text/Bildern/Vektorgrafiken (Shapes) in das PDF.

## Aktueller Status
- Initialisierung des Projekts.
- Modernes UI: Globales Dark Theme mit angepassten Farben, Rahmen und Hover-Effekten für ein echtes Native-Feeling. Die Anwendung verwendet nun ein hochwertiges Multi-Resolution App-Icon (16px bis 256px), das beim Build automatisch aus der Datei `icon.png` generiert wird (verhindert Pixelierung bei der `.exe`).
- Toolbar: Die Toolbar ist nun in zwei Reihen aufgeteilt (immer vollständig ausgeklappt) und mit Emojis als Icons versehen.
- Seiten werden vertikal gerendert.
- Zoom-Funktion mit QSettings implementiert.
- Elemente (Text, Bild, X, ✓, Unterschrift, Formen) werden wie bei einem Werkzeug (Tool-Modus) eingefügt: Button klicken, dann an die gewünschte Stelle im PDF klicken.
- Bei ausgewähltem Werkzeug wird anstelle des Mauszeigers direkt eine leicht transparente Vorschau (Ghost-Preview) des Elements angezeigt, exakt in der Größe und Farbe, in der es beim Klick eingefügt wird.
- Elemente sind via Drag & Drop verschiebbar und am rechten unteren Rand in der Größe skalierbar.
- Das Programm merkt sich für jedes Werkzeug (Text, Bild, X, ✓, Unterschrift, Formen) die zuletzt eingestellte Größe (Skalierung) und wendet diese beim nächsten Einfügen (sowie in der Vorschau) automatisch wieder an.
- **Kontextmenü (Floating Menu):** Sobald ein eingefügtes Element (Text, Form, etc.) fokussiert/angeklickt wird, erscheint direkt an der Maus ein kleines fliegendes Menü mit den wichtigsten Optionen für dieses Element (🎨 Farbe ändern, 🟩 Fill umschalten, 🗑️ Löschen). Das Menü verschwindet automatisch, während das Element gezogen oder in der Größe verändert wird.
- Elemente können per Rechtsklick oder durch Markieren und Drücken der `ENTF`-Taste gelöscht werden (zusätzlich zum neuen Kontextmenü).
- **Verlustfreies Speichern & Wiederherstellen (Neu):** Beim Speichern wird das Dokument nicht mehr "flachgeklopft". Die App bettet stattdessen die Original-PDF sowie eine unsichtbare JSON-Datei (`editor_state.json`) als Dateianhang (Embedded Files) in das PDF ein. Wenn du die bearbeitete PDF-Datei später erneut in der App öffnest, werden alle deine Elemente (Texte, Formen, Bilder) automatisch wieder in bewegliche, frei editierbare und löschbare Bausteine umgewandelt! Für andere PDF-Viewer (wie Adobe Acrobat oder Chrome) sieht das PDF dennoch aus wie ein ganz normales, fertig bearbeitetes Dokument.
- Formen (Rechteck, Kreis, Dreieck) werden beim Speichern direkt als verlustfreie, native Vektorgrafiken in die PDF-Datei geschrieben.
- **Umfassendes Fehler-Logging:** Die App nutzt das `logging`-Modul, um auf `DEBUG`-Level eine vollständige Historie aller Abläufe und Fehler (inklusive Tracebacks durch Überschreiben von `sys.excepthook`) aufzuzeichnen. Die Logs werden bei jedem App-Start überschrieben und in der `log.txt` abgelegt.
- **Executable (EXE) Build:** Ein Build-Skript (`build.ps1`) ist vorhanden, um die App jederzeit per PyInstaller als standalone `.exe`-Datei ohne Konsole (`--noconsole --onefile`) in den `dist`-Ordner zu kompilieren.
- **Smarter Dateiname beim Speichern:** Beim Speichern wird automatisch der Originalname des PDFs vorgeschlagen. Wurde das PDF manipuliert (z.B. Text, Formen, Bilder eingefügt), wird `_M` angehängt. Wurde zusätzlich eine Unterschrift eingefügt, wird ein `S` angehängt. Die App prüft nun vorab, ob bereits ein `_M` oder `_MS` am Ende des Dateinamens existiert, und entfernt dieses, um mehrfache Anhänge (wie `XYZ_M_M.pdf`) zu vermeiden. Beispiel: `XYZ.pdf` → `XYZ_MS.pdf`.
- **Highlight-Tool (Neu):** Ein Drag-to-Draw Werkzeug zum Markieren von Text. Der Nutzer wählt eine Farbe (Standard: Gelb), klickt dann auf 🖍️ Highlight und zieht mit der Maus ein Rechteck auf dem PDF auf. Das Rechteck wird leicht transparent (~30% Deckkraft) over den Text gelegt. Highlights sind verschiebbar, skalierbar (Resize-Handle unten rechts), per Kontextmenü löschbar und farblich veränderbar. Mehrere Highlights können hintereinander gezogen werden (Rechtsklick beendet den Modus). Beim Speichern wird das Highlight als natives fitz `draw_rect` mit `fill_opacity=0.3` in die PDF geschrieben. Der State (Position, Größe, Farbe) wird via `get_state`/`restore_state` vollständig gesichert und wiederhergestellt.
- **Settings & About (Neu):** Ein Zahnrad-Button (⚙️) oben rechts in der Toolbar öffnet ein Menü mit einem "About"-Dialog. Dieser zeigt Informationen zum App-Namen, der aktuellen Build-Nummer und dem Jahr des letzten Builds an. Zusätzlich gibt es nun einen **"Log"-Button**, der den Inhalt der `log.txt` Datei in einem scrollbaren Dialog anzeigt (nützlich für Debugging).
- **Automatisierte Build-Nummerierung:** Die App nutzt eine `version.json`, um die Build-Nummer zu tracken. Das `build.ps1`-Skript erhöht diese Nummer bei jedem Build automatisch um 1 und aktualisiert das Build-Jahr.
- **Default Downloads & Persistenz:** Beim ersten Öffnen/Einfügen einer PDF wird der Downloads-Ordner vorgeschlagen. Danach merkt sich die App den zuletzt genutzten Ordner (via `QSettings`), auch über einen Neustart hinweg. Als Speicherort wird standardmäßig der Ursprungsordner der PDF vorgeschlagen; Änderungen am Speicherort werden für die Dauer der aktuellen Sitzung (Session) beibehalten.
- **Set as Default PDF Editor (Neu):** Im Einstellungsmenü gibt es nun die Option "📌 Set as default PDF editor". Wenn diese gedrückt wird, registriert sich die Anwendung als Standard-Handler für PDF-Dateien. Dies wird auf **Windows** (Registry), **Linux** (Desktop-Datei & xdg-mime) unterstützt; auf **macOS** wird eine Anleitung zur manuellen Einstellung angezeigt. Die App wurde zudem aktualisiert, um PDF-Dateien direkt zu öffnen, wenn sie über die Kommandozeile (z.B. durch Doppelklick im Explorer) gestartet wird. **Zusätzlich fragt die App nun beim allerersten Start automatisch nach, ob sie als Standard-Editor festgelegt werden soll.**
- **Undo & Redo (Neu):** Die App verfügt nun über eine vollständige Historie für bis zu 254 Aktionen. Alle Änderungen (Hinzufügen/Löschen von Elementen, Verschieben, Skalieren, Farbänderungen sowie Seitenoperationen) können über die neuen Buttons in der Toolbar oder via `STRG+Z` (Undo) und `STRG+Y` (Redo) rückgängig gemacht oder wiederholt werden. Die ältesten Schritte werden automatisch gelöscht, sobald das Limit überschritten wird.
- **Pfeiltasten-Nudging (Neu):** Wenn ein Element ausgewählt ist, kann es mit den Pfeiltasten (↑↓←→) pixelgenau um je 1px verschoben werden. Ist kein Element selektiert, scrollen die Pfeiltasten wie gewohnt das PDF.
- README.md (root) und github_export/README.md wurden mit den neuesten Funktionen (Undo/Redo, Highlight & Comment) aktualisiert.
- **Cursor Bug Fixes (Neu):** Behoben, dass der Mauszeiger beim Bewegen über das PDF unkontrolliert flackert/verschwindet. Der Vorschau-Cursor (Ghost Item) wird nun über allen anderen Elementen gerendert (Z-Value `10000.0`). Das Übersteuern des Mauszeigers bei Hover-Events auf Elementen wurde für aktive Werkzeug-Modi deaktiviert. Außerdem kann der aktive Werkzeug-Modus nun auch per `ESC`-Taste abgebrochen werden.
- **Direktdruck (Neu):** Ein `Print PDF`-Button in der Toolbar 1 und Tastatur-Shortcut `STRG + P`. Übergibt den aktuellen Stand der QGraphicsScene (unter Ausblendung von Hilfslinien und Vorschau-Objekten) als hochauflösenden Vektor-Print an das System-Druckmenü (QPrintDialog).
- **Startup-Argumente & Windows-Registrierung Fix (Neu):** Robusteres Parsen von Dateipfaden, die beim Start über die Windows-Befehlszeile oder "Öffnen mit..." übergeben werden (Bereinigung von Anführungszeichen, Absolutpfad-Auflösung und Behandlung von Pfaden mit Leerzeichen, die fälschlicherweise getrennt übergeben wurden). Außerdem wird das Hauptfenster nun vor dem Laden des PDFs maximiert und die Windows-Registrierung für Dateizuordnungen wurde modernisiert (`OpenWithProgids` statt Direktüberschreibung der Erweiterung), um Microsofts Sicherheitsprüfungen (UserChoice-Hashes) unter Windows 10/11 nicht zu triggern.
- **Seitenanzeige Fix (Neu):** Die Anzeige der Seitenzahl (z. B. `Page: 1 / 3`) funktionierte zuvor nur, wenn Elemente fokussiert/verschoben wurden. Die `on_scroll_changed`-Funktion wurde nun ausprogrammiert und aktualisiert die Anzeige jetzt dynamisch beim Scrollen sowie direkt nach dem Laden des Dokuments.
- **Datum im Dateinamen (Neu):** Hinzufügen einer Checkbox "Add date to filename" in das Einstellungsmenü (Standard: Aktiviert, Wert persistent über QSettings gespeichert). Beim Speichern wird das aktuelle Datum als Präfix ("dd_mm_yyyy") vor den Dateinamen gesetzt. Ein Regex prüft vorab, ob bereits ein Datum (dd_mm_yyyy, dd-mm-yyyy, dd.mm.yyyy, dd/mm/yyyy, dd_mm_yy, dd_mm etc.) am Anfang des Dateinamens existiert, um doppelte Präfixe zu verhindern.
- **Text Spacing Input Feld (Neu):** Breite des Spacing-Eingabefelds auf 90px erhöht, damit Zahlen nicht abgeschnitten werden. Die Schrittweite für Pfeil-Buttons sowie Pfeiltasten (Up/Down) auf 0,5 angepasst (vorher 1,0).
- **Schriftarten-Vorschau & Dropdown (Neu):** Jede Schriftart im Dropdown-Menü wird in ihrer jeweiligen Typografie dargestellt (`FontRole`), inklusive Echtzeit-Vorschau der gewählten Schrift im geschlossenen Dropdown-Feld.
- **Element Duplizieren / Kopieren (Neu):** Ein `📋`-Copy-Icon im schwebenden Kontextmenü ermöglicht das sofortige Klonen jedes ausgewählten Elements (Text, Formen, Markierungen, Bilder, Stempel, Zeichnungen) an die aktuelle Mausposition. Das neue Element wird sofort zentriert unter dem Mauszeiger platziert und direkt fokussiert.
- **Insert PDF Default-Position (Neu):** Beim Einfügen eines PDFs via `Insert PDF` fragt der Dialog standardmäßig nicht mehr nach Seite 1, sondern schlägt als Default immer die letzte Seite (`total_pages`) vor, da das Anhängen weiterer Seiten an das Dokument der häufigste Anwendungsfall ist.
- **Release V2.4.1:** Als GitHub Release veröffentlicht inklusive hochgeladener `Minimal_PDF_Editor.exe` (Build #57).
- `memory.md` wird gepflegt.








