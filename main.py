import sys
import fitz  # PyMuPDF
import logging
import traceback
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
                             QGraphicsPixmapItem, QGraphicsTextItem, QGraphicsPathItem, QVBoxLayout, QHBoxLayout,
                             QWidget, QPushButton, QFileDialog, QToolBar,
                             QInputDialog, QMessageBox, QStyle, QColorDialog, QDoubleSpinBox, QLabel)

# Configure comprehensive error logging to log.txt (overwriting on each start)
logging.basicConfig(
    filename='log.txt',
    filemode='w',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def global_exception_handler(exc_type, exc_value, exc_traceback):
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = global_exception_handler
logger.info("Application started")
from PyQt6.QtGui import QImage, QPixmap, QFont, QTransform, QWheelEvent, QPen, QColor, QPainter, QCursor, QIcon, QPolygonF, QFontMetricsF, QPainterPath
from PyQt6.QtCore import Qt, QSettings, QRectF, QByteArray, QBuffer, QIODevice, QPointF, QStandardPaths
import os
import json
import base64

DPI = 150
PDF_ZOOM = DPI / 72.0  # Base rendering zoom from PDF to Scene

class MovableTextItem(QGraphicsTextItem):
    def __init__(self, text, font_size=16, letter_spacing=0.0):
        super().__init__(text)
        self.setFlags(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsTextItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1.0)
        self.resizing = False
        self.handle_size = 10
        font = QFont("Arial")
        font.setPointSizeF(float(font_size))
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, letter_spacing)
        self.setFont(font)
        self.document().setDocumentMargin(0)
        self.setDefaultTextColor(Qt.GlobalColor.black)
        self.type_str = "text"
        self.font_size = font_size
        self.letter_spacing = letter_spacing

    def get_handle_size(self):
        scale = self.scale() if self.scale() > 0 else 1.0
        return 12.0 / scale

    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def hoverMoveEvent(self, event):
        rect = self.boundingRect()
        h_size = self.get_handle_size()
        if event.pos().x() >= rect.right() - h_size and event.pos().y() >= rect.bottom() - h_size:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if self.scene() and self.scene().views():
            editor = self.scene().views()[0].parent_editor
            if hasattr(editor, 'floating_menu'):
                editor.floating_menu.hide()

        if event.button() == Qt.MouseButton.RightButton:
            if self.scene():
                self.scene().removeItem(self)
            event.accept()
            return
            
        super().mousePressEvent(event)
        
        rect = self.boundingRect()
        h_size = self.get_handle_size()
        if event.pos().x() >= rect.right() - h_size and event.pos().y() >= rect.bottom() - h_size:
            self.setSelected(True)
            self.resizing = True
            self.orig_scale = self.scale()
            self.orig_scene_pos = event.scenePos()
            event.accept()
        else:
            self.resizing = False

    def mouseMoveEvent(self, event):
        if self.resizing:
            diff = event.scenePos() - self.orig_scene_pos
            rect = self.boundingRect()
            orig_scene_width = rect.width() * self.orig_scale
            new_scene_width = orig_scene_width + diff.x()
            if new_scene_width > 10:
                new_scale = new_scene_width / rect.width()
                self.setScale(new_scale)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            if self.scene() and self.scene().views():
                editor = self.scene().views()[0].parent_editor
                if hasattr(editor, 'last_scales'):
                    editor.last_scales[self.type_str] = self.scale()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
        if self.scene() and self.scene().views():
            editor = self.scene().views()[0].parent_editor
            if hasattr(editor, 'show_floating_menu') and self.isSelected():
                editor.show_floating_menu()

    def mouseDoubleClickEvent(self, event):
        rect = self.boundingRect()
        h_size = self.get_handle_size()
        # If clicking on the resize handle, ignore custom editing logic
        if event.pos().x() >= rect.right() - h_size and event.pos().y() >= rect.bottom() - h_size:
            super().mouseDoubleClickEvent(event)
            return

        parent_widget = self.scene().views()[0] if self.scene() and self.scene().views() else None
        text, ok = QInputDialog.getMultiLineText(parent_widget, "Edit Text", "Edit text:", self.toPlainText())
        if ok:
            self.setPlainText(text)
            # Update floating menu position if needed
            if parent_widget and hasattr(parent_widget.parent_editor, 'show_floating_menu') and self.isSelected():
                parent_widget.parent_editor.show_floating_menu()
        event.accept()

    def paint(self, painter, option, widget=None):
        state = option.state
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)
        option.state = state
        
        if self.isSelected():
            scale = self.scale() if self.scale() > 0 else 1.0
            pen_width = 2.0 / scale
            painter.setPen(QPen(QColor(0, 120, 215), pen_width, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            rect = self.boundingRect()
            painter.drawRect(rect.adjusted(pen_width/2, pen_width/2, -pen_width/2, -pen_width/2))
            
            h_size = self.get_handle_size()
            painter.setBrush(QColor(0, 120, 215))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(QRectF(rect.right() - h_size, rect.bottom() - h_size, h_size, h_size))

class MovablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, pixmap, img_path=None, item_type="image"):
        super().__init__(pixmap)
        self.setFlags(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable | 
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable |
                      QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.resizing = False
        self.handle_size = 10
        self.img_path = img_path
        self.type_str = item_type
        self.scale_x = 1.0
        self.scale_y = 1.0

    def setScale(self, scale):
        self.scale_x = float(scale)
        self.scale_y = float(scale)
        self.setTransform(QTransform().scale(self.scale_x, self.scale_y))

    def setScaleXY(self, sx, sy):
        self.scale_x = float(sx)
        self.scale_y = float(sy)
        self.setTransform(QTransform().scale(self.scale_x, self.scale_y))

    def get_handle_size(self):
        scale = max(self.scale_x, self.scale_y)
        if scale <= 0: scale = 1.0
        return 12.0 / scale

    def get_handle_area(self, pos):
        rect = self.boundingRect()
        h_size = self.get_handle_size()
        x, y = pos.x(), pos.y()
        in_right = x >= rect.right() - h_size
        in_bottom = y >= rect.bottom() - h_size
        
        if in_right and in_bottom:
            return "corner"
        elif in_right:
            return "right"
        elif in_bottom:
            return "bottom"
        return None

    def redraw(self):
        if not hasattr(self, 'color'): return
        self.prepareGeometryChange()
        bw = getattr(self, 'border_width', 3)
        if self.type_str == "check":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 15, 12, 25)
            painter.drawLine(12, 25, 28, 5)
            painter.end()
            self.setPixmap(pixmap)
        elif self.type_str == "cross":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 5, 25, 25)
            painter.drawLine(25, 5, 5, 25)
            painter.end()
            self.setPixmap(pixmap)
        elif self.type_str in ["rect", "circle", "triangle"]:
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            if getattr(self, 'filled', False):
                painter.setBrush(self.color)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.type_str == "rect":
                painter.drawRect(5, 5, 50, 50)
            elif self.type_str == "circle":
                painter.drawEllipse(5, 5, 50, 50)
            elif self.type_str == "triangle":
                poly = QPolygonF([QPointF(30, 5), QPointF(55, 55), QPointF(5, 55)])
                painter.drawPolygon(poly)
            painter.end()
            self.setPixmap(pixmap)
        elif self.type_str == "line":
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 30, 55, 30)
            painter.end()
            self.setPixmap(pixmap)
        elif self.type_str == "brush":
            if hasattr(self, 'drawing_points') and self.drawing_points:
                pad = 20
                rect = self.boundingRect()
                w = int(rect.width()) if rect.width() > 0 else 60
                h = int(rect.height()) if rect.height() > 0 else 60
                pixmap = QPixmap(w, h)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                pen = QPen(self.color, bw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                for i, p in enumerate(self.drawing_points):
                    if i == 0:
                        path.moveTo(p[0], p[1])
                    else:
                        path.lineTo(p[0], p[1])
                painter.drawPath(path)
                painter.end()
                self.setPixmap(pixmap)

    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def hoverMoveEvent(self, event):
        area = self.get_handle_area(event.pos())
        if area == "corner":
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif area == "right":
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif area == "bottom":
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if self.scene() and self.scene().views():
            editor = self.scene().views()[0].parent_editor
            if hasattr(editor, 'floating_menu'):
                editor.floating_menu.hide()

        if event.button() == Qt.MouseButton.RightButton:
            if self.scene():
                self.scene().removeItem(self)
            event.accept()
            return
            
        super().mousePressEvent(event)
        
        area = self.get_handle_area(event.pos())
        if area:
            self.setSelected(True)
            self.resizing = True
            self.resize_mode = area
            self.orig_scale_x = self.scale_x
            self.orig_scale_y = self.scale_y
            self.orig_scene_pos = event.scenePos()
            event.accept()
        else:
            self.resizing = False

    def mouseMoveEvent(self, event):
        if self.resizing:
            diff = event.scenePos() - self.orig_scene_pos
            # Map the scene diff to the item's local rotation orientation
            trans = QTransform().rotate(-self.rotation())
            local_diff = trans.map(diff)
            
            rect = self.boundingRect()
            orig_scene_width = rect.width() * self.orig_scale_x
            orig_scene_height = rect.height() * self.orig_scale_y
            
            new_scale_x = self.orig_scale_x
            new_scale_y = self.orig_scale_y
            
            if self.resize_mode == "corner":
                new_scene_width = orig_scene_width + local_diff.x()
                if new_scene_width > 10:
                    scale_factor = new_scene_width / orig_scene_width
                    new_scale_x = self.orig_scale_x * scale_factor
                    new_scale_y = self.orig_scale_y * scale_factor
            elif self.resize_mode == "right":
                new_scene_width = orig_scene_width + local_diff.x()
                if new_scene_width > 10:
                    new_scale_x = new_scene_width / rect.width()
            elif self.resize_mode == "bottom":
                new_scene_height = orig_scene_height + local_diff.y()
                if new_scene_height > 10:
                    new_scale_y = new_scene_height / rect.height()
                    
            self.setScaleXY(new_scale_x, new_scale_y)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            if self.scene() and self.scene().views():
                editor = self.scene().views()[0].parent_editor
                if hasattr(editor, 'last_scales'):
                    # Save the max scale to use for new items
                    editor.last_scales[self.type_str] = max(self.scale_x, self.scale_y)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

        if self.scene() and self.scene().views():
            editor = self.scene().views()[0].parent_editor
            if hasattr(editor, 'show_floating_menu') and self.isSelected():
                editor.show_floating_menu()

    def paint(self, painter, option, widget=None):
        state = option.state
        option.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)
        option.state = state
        
        if self.isSelected():
            scale_x = self.scale_x if self.scale_x > 0 else 1.0
            scale_y = self.scale_y if self.scale_y > 0 else 1.0
            
            # Use inverse scaling for the pen so the border looks uniform
            painter.save()
            painter.setTransform(QTransform().scale(1/scale_x, 1/scale_y), True)
            
            rect = self.boundingRect()
            scaled_rect = QRectF(rect.x() * scale_x, rect.y() * scale_y, 
                                 rect.width() * scale_x, rect.height() * scale_y)
            
            pen_width = 2.0
            painter.setPen(QPen(QColor(0, 120, 215), pen_width, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(scaled_rect.adjusted(pen_width/2, pen_width/2, -pen_width/2, -pen_width/2))
            
            h_size = 12.0
            painter.setBrush(QColor(0, 120, 215))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Corner
            painter.drawRect(QRectF(scaled_rect.right() - h_size, scaled_rect.bottom() - h_size, h_size, h_size))
            # Right edge
            painter.drawRect(QRectF(scaled_rect.right() - h_size, scaled_rect.center().y() - h_size/2, h_size, h_size))
            # Bottom edge
            painter.drawRect(QRectF(scaled_rect.center().x() - h_size/2, scaled_rect.bottom() - h_size, h_size, h_size))
            
            painter.restore()

class FloatingMenu(QWidget):
    def __init__(self, editor):
        super().__init__(editor.view)
        self.editor = editor
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        self.setStyleSheet("""
            QWidget {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 6px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                color: #cccccc;
            }
            QPushButton:hover { background-color: #3e3e42; color: #ffffff; }
            QPushButton:pressed { background-color: #007acc; color: #ffffff; }
        """)
        
        self.btn_color = QPushButton("🎨")
        self.btn_color.setToolTip("Change Color")
        self.btn_color.clicked.connect(self.editor.change_selected_color)
        self.layout.addWidget(self.btn_color)
        
        self.btn_fill = QPushButton("🟩")
        self.btn_fill.setToolTip("Toggle Fill")
        self.btn_fill.clicked.connect(self.editor.toggle_selected_fill)
        self.layout.addWidget(self.btn_fill)
        
        self.btn_delete = QPushButton("🗑️")
        self.btn_delete.setToolTip("Delete Item")
        self.btn_delete.clicked.connect(self.editor.delete_selected)
        self.layout.addWidget(self.btn_delete)
        
        self.hide()

    def show_for_item(self, item):
        self.btn_color.setVisible(item.type_str in ["text", "check", "cross", "rect", "circle", "triangle"])
        self.btn_fill.setVisible(item.type_str in ["rect", "circle", "triangle"])
        
        if item.type_str in ["rect", "circle", "triangle"]:
            filled = getattr(item, 'filled', False)
            self.btn_fill.setText("🟩" if filled else "⬛")
            
        self.adjustSize()
        self.show()

class PDFGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.parent_editor = parent

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        scene_pos = self.mapToScene(event.pos())
        
        if self.parent_editor.current_tool == "brush" and getattr(self.parent_editor, 'is_drawing', False):
            self.parent_editor.continue_drawing(scene_pos)
            event.accept()
            return
            
        if self.parent_editor.current_tool and self.parent_editor.ghost_item:
            rect = self.parent_editor.ghost_item.boundingRect()
            scale = self.parent_editor.ghost_item.scale()
            if self.parent_editor.current_tool == "text":
                self.parent_editor.ghost_item.setPos(scene_pos.x(), scene_pos.y())
            else:
                self.parent_editor.ghost_item.setPos(scene_pos.x() - (rect.width()*scale) / 2, scene_pos.y() - (rect.height()*scale) / 2)

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.parent_editor.zoom_in()
            else:
                self.parent_editor.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if self.parent_editor.current_tool:
            if event.button() == Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                if self.parent_editor.current_tool == "brush":
                    self.parent_editor.start_drawing(scene_pos)
                else:
                    self.parent_editor.apply_tool(scene_pos)
                event.accept()
                return
            elif event.button() == Qt.MouseButton.RightButton:
                self.parent_editor.current_tool = None
                if self.parent_editor.ghost_item:
                    self.scene().removeItem(self.parent_editor.ghost_item)
                    self.parent_editor.ghost_item = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parent_editor.current_tool == "brush" and getattr(self.parent_editor, 'is_drawing', False):
            if event.button() == Qt.MouseButton.LeftButton:
                self.parent_editor.finish_drawing()
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            for item in self.scene().selectedItems():
                self.scene().removeItem(item)
            event.accept()
        else:
            super().keyPressEvent(event)

class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Editor App")
        self.setGeometry(100, 100, 1024, 768)
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.setWindowIcon(self.create_app_icon())
        
        self.settings = QSettings("MyCompany", "PDFEditorApp")
        
        self.doc = None
        self.original_pdf_bytes = None
        self.original_filename = None
        self.current_tool = None
        self.ghost_item = None
        self.last_scales = {}
        self.mark_color = QColor(Qt.GlobalColor.black)
        self.shape_filled = False
        self.shape_border_width = 3
        self.is_drawing = False
        self.current_drawing_points = []
        self.current_drawing_path = None
        
        app_data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        os.makedirs(app_data_dir, exist_ok=True)
        self.signature_path = os.path.join(app_data_dir, "signature.png")
        
        self.page_rects = [] # stores (page_num, start_y, height)
        self.pdf_bg_items = []
        
        # Load last zoom or default to 1.0
        try:
            self.view_zoom = float(self.settings.value("view_zoom", 1.0))
        except (TypeError, ValueError):
            self.view_zoom = 1.0
        
        # Central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Global Dark Theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QGraphicsView {
                background-color: #2d2d30;
                border: none;
            }
            QToolBar {
                background-color: #252526;
                border-bottom: 1px solid #3e3e42;
                padding: 8px;
                spacing: 8px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                color: #cccccc;
            }
            QPushButton:hover {
                background-color: #3e3e42;
                border-color: #555555;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #007acc;
                border-color: #007acc;
                color: #ffffff;
            }
            QToolBar::separator {
                width: 2px;
                background-color: #3e3e42;
                margin: 0 8px;
            }
        """)

        # Toolbar 1 (File & View)
        self.toolbar1 = QToolBar()
        self.toolbar1.setMovable(False)
        self.addToolBar(self.toolbar1)
        
        self.btn_open = QPushButton("📂 Open PDF")
        self.btn_open.clicked.connect(self.open_pdf)
        self.toolbar1.addWidget(self.btn_open)
        
        self.btn_edit = QPushButton("✏️ Edit PDF")
        self.btn_edit.clicked.connect(self.edit_pdf)
        self.toolbar1.addWidget(self.btn_edit)
        
        self.btn_save = QPushButton("💾 Save PDF")
        self.btn_save.setShortcut("Ctrl+S")
        self.btn_save.clicked.connect(self.save_pdf)
        self.toolbar1.addWidget(self.btn_save)
        
        self.toolbar1.addSeparator()
        
        self.btn_zoom_in = QPushButton("🔍 Zoom In")
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.toolbar1.addWidget(self.btn_zoom_in)
        
        self.btn_zoom_out = QPushButton("🔎 Zoom Out")
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.toolbar1.addWidget(self.btn_zoom_out)
        
        self.btn_zoom_reset = QPushButton("🔄 Reset Zoom")
        self.btn_zoom_reset.clicked.connect(self.reset_zoom)
        self.toolbar1.addWidget(self.btn_zoom_reset)

        self.addToolBarBreak()

        # Toolbar 2 (Tools)
        self.toolbar2 = QToolBar()
        self.toolbar2.setMovable(False)
        self.addToolBar(self.toolbar2)
        
        self.btn_text = QPushButton("📝 Text")
        self.btn_text.clicked.connect(self.add_text)
        self.toolbar2.addWidget(self.btn_text)
        
        lbl_spacing = QLabel(" Spacing:")
        lbl_spacing.setStyleSheet("color: #cccccc; font-weight: bold; margin-left: 5px;")
        self.toolbar2.addWidget(lbl_spacing)
        
        self.spin_spacing = QDoubleSpinBox()
        self.spin_spacing.setRange(-20.0, 50.0)
        self.spin_spacing.setValue(0.0)
        self.spin_spacing.setSingleStep(1.0)
        self.spin_spacing.setDecimals(1)
        self.spin_spacing.setFixedWidth(70)
        self.spin_spacing.valueChanged.connect(self.update_spacing)
        self.toolbar2.addWidget(self.spin_spacing)
        
        self.btn_check = QPushButton("✅ Check")
        self.btn_check.clicked.connect(self.add_check)
        self.toolbar2.addWidget(self.btn_check)
        
        self.btn_cross = QPushButton("❌ Cross")
        self.btn_cross.clicked.connect(self.add_cross)
        self.toolbar2.addWidget(self.btn_cross)
        
        self.toolbar2.addSeparator()
        
        self.btn_rect = QPushButton("⬛ Rect")
        self.btn_rect.clicked.connect(self.add_rect)
        self.toolbar2.addWidget(self.btn_rect)
        
        self.btn_circle = QPushButton("⭕ Circle")
        self.btn_circle.clicked.connect(self.add_circle)
        self.toolbar2.addWidget(self.btn_circle)
        
        self.btn_triangle = QPushButton("🔺 Triangle")
        self.btn_triangle.clicked.connect(self.add_triangle)
        self.toolbar2.addWidget(self.btn_triangle)
        
        self.btn_line = QPushButton("➖ Line")
        self.btn_line.clicked.connect(self.add_line)
        self.toolbar2.addWidget(self.btn_line)
        
        self.btn_brush = QPushButton("🖌️ Brush")
        self.btn_brush.clicked.connect(self.add_brush)
        self.toolbar2.addWidget(self.btn_brush)
        
        self.btn_filled = QPushButton("🟩 Fill: OFF")
        self.btn_filled.clicked.connect(self.toggle_filled)
        self.btn_filled.setCheckable(True)
        self.toolbar2.addWidget(self.btn_filled)
        
        lbl_border = QLabel(" Line Width:")
        lbl_border.setStyleSheet("color: #cccccc; font-weight: bold; margin-left: 5px;")
        self.toolbar2.addWidget(lbl_border)
        
        self.spin_border = QDoubleSpinBox()
        self.spin_border.setRange(0.0, 20.0)
        self.spin_border.setValue(3.0)
        self.spin_border.setSingleStep(1.0)
        self.spin_border.setDecimals(1)
        self.spin_border.setFixedWidth(70)
        self.spin_border.valueChanged.connect(self.update_border)
        self.toolbar2.addWidget(self.spin_border)
        
        lbl_rot = QLabel(" Rotation:")
        lbl_rot.setStyleSheet("color: #cccccc; font-weight: bold; margin-left: 5px;")
        self.toolbar2.addWidget(lbl_rot)
        
        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-360.0, 360.0)
        self.spin_rotation.setValue(0.0)
        self.spin_rotation.setSingleStep(15.0)
        self.spin_rotation.setDecimals(1)
        self.spin_rotation.setFixedWidth(80)
        self.spin_rotation.valueChanged.connect(self.update_rotation)
        self.toolbar2.addWidget(self.spin_rotation)
        
        self.addToolBarBreak()
        
        # Toolbar 3 (Media & Settings)
        self.toolbar3 = QToolBar()
        self.toolbar3.setMovable(False)
        self.addToolBar(self.toolbar3)
        
        self.btn_color = QPushButton("🎨 Color")
        self.btn_color.clicked.connect(self.set_mark_color)
        self.toolbar3.addWidget(self.btn_color)
        
        self.btn_image = QPushButton("🖼️ Image")
        self.btn_image.clicked.connect(self.add_image)
        self.toolbar3.addWidget(self.btn_image)
        
        self.toolbar3.addSeparator()
        
        self.btn_set_sig = QPushButton("⚙️ Set Signature")
        self.btn_set_sig.clicked.connect(self.set_signature)
        self.toolbar3.addWidget(self.btn_set_sig)
        
        self.btn_add_sig = QPushButton("🖋️ Add Signature")
        self.btn_add_sig.clicked.connect(self.add_signature)
        self.toolbar3.addWidget(self.btn_add_sig)
        
        self.toolbar3.addSeparator()
        
        self.lbl_page_info = QLabel(" Page: - / - ")
        self.lbl_page_info.setStyleSheet("color: #cccccc; font-weight: bold; margin-left: 5px; margin-right: 5px;")
        self.toolbar3.addWidget(self.lbl_page_info)
        
        self.btn_add_page = QPushButton("📄 Add Blank Page")
        self.btn_add_page.clicked.connect(self.add_blank_page)
        self.toolbar3.addWidget(self.btn_add_page)
        
        self.btn_insert_pdf = QPushButton("📑 Insert PDF")
        self.btn_insert_pdf.clicked.connect(self.insert_pdf)
        self.toolbar3.addWidget(self.btn_insert_pdf)
        
        self.btn_del_page = QPushButton("🗑️ Delete Page")
        self.btn_del_page.clicked.connect(self.delete_current_page)
        self.toolbar3.addWidget(self.btn_del_page)

        # Graphics View
        self.scene = QGraphicsScene()
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.view = PDFGraphicsView(self.scene, self)
        self.view.verticalScrollBar().valueChanged.connect(self.on_scroll_changed)
        self.layout.addWidget(self.view)
        
        self.floating_menu = FloatingMenu(self)
        
        self.apply_zoom()

    def create_app_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor("#007acc"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(4, 4, 56, 56, 12, 12)
        
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Arial", 16, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(4, 4, 56, 56), Qt.AlignmentFlag.AlignCenter, "PDF")
        
        painter.end()
        return QIcon(pixmap)

    def zoom_in(self):
        self.view_zoom *= 1.2
        self.apply_zoom()

    def zoom_out(self):
        self.view_zoom /= 1.2
        self.apply_zoom()
        
    def reset_zoom(self):
        self.view_zoom = 1.0
        self.apply_zoom()

    def apply_zoom(self):
        self.settings.setValue("view_zoom", self.view_zoom)
        transform = QTransform()
        transform.scale(self.view_zoom, self.view_zoom)
        self.view.setTransform(transform)

    def show_floating_menu(self):
        items = self.scene.selectedItems()
        if len(items) == 1:
            item = items[0]
            self.floating_menu.show_for_item(item)
            
            rect = item.sceneBoundingRect()
            top_center_scene = QPointF(rect.center().x(), rect.top())
            view_pos = self.view.mapFromScene(top_center_scene)
            
            x = view_pos.x() - (self.floating_menu.width() // 2)
            y = view_pos.y() - self.floating_menu.height() - 15
            
            if x < 10:
                x = 10
            elif x + self.floating_menu.width() > self.view.width() - 10:
                x = self.view.width() - self.floating_menu.width() - 10
                
            if y < 10:
                bottom_center_scene = QPointF(rect.center().x(), rect.bottom())
                bottom_view_pos = self.view.mapFromScene(bottom_center_scene)
                y = bottom_view_pos.y() + 15
                
            self.floating_menu.move(int(x), int(y))
            self.floating_menu.raise_()
        else:
            self.floating_menu.hide()

    def change_selected_color(self):
        items = self.scene.selectedItems()
        if not items: return
        item = items[0]
        
        current_color = getattr(item, 'color', Qt.GlobalColor.black)
        if isinstance(item, MovableTextItem):
            current_color = item.defaultTextColor()
            
        color = QColorDialog.getColor(QColor(current_color), self, "Select Item Color")
        if color.isValid():
            if isinstance(item, MovableTextItem):
                item.setDefaultTextColor(color)
            elif isinstance(item, MovablePixmapItem):
                item.color = color
                item.redraw()

    def toggle_selected_fill(self):
        items = self.scene.selectedItems()
        if not items: return
        item = items[0]
        if isinstance(item, MovablePixmapItem) and item.type_str in ["rect", "circle", "triangle"]:
            item.filled = not getattr(item, 'filled', False)
            item.redraw()
            self.show_floating_menu()

    def delete_selected(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
        self.floating_menu.hide()

    def on_selection_changed(self):
        self.show_floating_menu()
        items = self.scene.selectedItems()
        if len(items) == 1:
            if isinstance(items[0], MovableTextItem):
                self.spin_spacing.blockSignals(True)
                self.spin_spacing.setValue(items[0].letter_spacing)
                self.spin_spacing.blockSignals(False)
            elif isinstance(items[0], MovablePixmapItem) and hasattr(items[0], 'border_width'):
                self.spin_border.blockSignals(True)
                self.spin_border.setValue(items[0].border_width)
                self.spin_border.blockSignals(False)

    def update_border(self, val):
        self.shape_border_width = val
        if self.current_tool in ["check", "cross", "rect", "circle", "triangle", "line", "brush"] and self.ghost_item:
            current = self.current_tool
            self.set_tool(current)
            
        for item in self.scene.selectedItems():
            if isinstance(item, MovablePixmapItem) and item.type_str in ["check", "cross", "rect", "circle", "triangle", "line", "brush"]:
                item.border_width = val
                item.redraw()

    def update_rotation(self, val):
        for item in self.scene.selectedItems():
            if isinstance(item, (MovablePixmapItem, MovableTextItem)):
                rect = item.boundingRect()
                item.setTransformOriginPoint(rect.center())
                item.setRotation(val)

    def update_spacing(self, val):
        if self.current_tool == "text" and self.ghost_item:
            font = self.ghost_item.font()
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, val)
            self.ghost_item.setFont(font)
            # Reposition ghost item (left-aligned for text)
            scale = self.ghost_item.scale()
            pos = self.view.mapFromGlobal(QCursor.pos())
            scene_pos = self.view.mapToScene(pos)
            self.ghost_item.setPos(scene_pos.x(), scene_pos.y())
            
        for item in self.scene.selectedItems():
            if isinstance(item, MovableTextItem):
                item.letter_spacing = val
                font = item.font()
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, val)
                item.setFont(font)

    def open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)")
        if file_path:
            # Store the original filename (without extension) for save suggestions
            self.original_filename = os.path.splitext(os.path.basename(file_path))[0]
            
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
                
            temp_doc = fitz.open("pdf", raw_bytes)
            
            if "original_pdf" in temp_doc.embfile_names() and "editor_state" in temp_doc.embfile_names():
                self.original_pdf_bytes = temp_doc.embfile_get("original_pdf")
                state_json = temp_doc.embfile_get("editor_state").decode("utf-8")
                self.doc = fitz.open("pdf", self.original_pdf_bytes)
                self.load_pdf()
                self.restore_state(state_json)
            else:
                self.original_pdf_bytes = raw_bytes
                self.doc = temp_doc
                self.load_pdf()

    def load_pdf(self):
        if not self.doc: return
        self.scene.clear()
        self.page_rects = []
        self.pdf_bg_items = []
        
        current_y = 0
        spacing = 20 # pixels between pages
        
        mat = fitz.Matrix(PDF_ZOOM, PDF_ZOOM)
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            
            bg_item = self.scene.addPixmap(pixmap)
            bg_item.setPos(0, current_y)
            self.pdf_bg_items.append(bg_item)
            
            self.page_rects.append({
                'page_num': page_num,
                'start_y': current_y,
                'height': pix.height
            })
            
            current_y += pix.height + spacing
            
        self.scene.setSceneRect(self.scene.itemsBoundingRect())
        self.on_scroll_changed()

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        if tool_name == "brush":
            self.view.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.view.setCursor(Qt.CursorShape.BlankCursor)
        
        if self.ghost_item:
            self.scene.removeItem(self.ghost_item)
            self.ghost_item = None
            
        bw = self.shape_border_width
        
        if tool_name == "text":
            self.ghost_item = QGraphicsTextItem("Text")
            font = QFont("Arial", 16)
            self.ghost_item.setFont(font)
            self.ghost_item.setDefaultTextColor(Qt.GlobalColor.black)
        elif tool_name == "check":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 15, 12, 25)
            painter.drawLine(12, 25, 28, 5)
            painter.end()
            self.ghost_item = QGraphicsPixmapItem(pixmap)
        elif tool_name == "cross":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 5, 25, 25)
            painter.drawLine(25, 5, 5, 25)
            painter.end()
            self.ghost_item = QGraphicsPixmapItem(pixmap)
        elif tool_name in ["rect", "circle", "triangle"]:
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.shape_filled:
                painter.setBrush(self.mark_color)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
            if tool_name == "rect":
                painter.drawRect(5, 5, 50, 50)
            elif tool_name == "circle":
                painter.drawEllipse(5, 5, 50, 50)
            elif tool_name == "triangle":
                poly = QPolygonF([QPointF(30, 5), QPointF(55, 55), QPointF(5, 55)])
                painter.drawPolygon(poly)
                
            painter.end()
            self.ghost_item = QGraphicsPixmapItem(pixmap)
        elif tool_name == "line":
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 30, 55, 30)
            painter.end()
            self.ghost_item = QGraphicsPixmapItem(pixmap)
        elif tool_name == "image":
            self.ghost_item = QGraphicsTextItem("🖼️")
            font = QFont("Arial", 28)
            self.ghost_item.setFont(font)
        elif tool_name == "signature":
            pixmap = QPixmap(self.signature_path)
            if pixmap.width() > 200:
                pixmap = pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            self.ghost_item = QGraphicsPixmapItem(pixmap)

        if self.ghost_item:
            self.ghost_item.setOpacity(0.5)
            scale = self.last_scales.get(tool_name, 1.0)
            self.ghost_item.setScale(scale)
            self.scene.addItem(self.ghost_item)
            pos = self.view.mapFromGlobal(QCursor.pos())
            scene_pos = self.view.mapToScene(pos)
            rect = self.ghost_item.boundingRect()
            if tool_name == "text":
                self.ghost_item.setPos(scene_pos.x(), scene_pos.y())
            else:
                self.ghost_item.setPos(scene_pos.x() - (rect.width()*scale) / 2, scene_pos.y() - (rect.height()*scale) / 2)

    def apply_tool(self, pos):
        tool = self.current_tool
        self.current_tool = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        
        if self.ghost_item:
            self.scene.removeItem(self.ghost_item)
            self.ghost_item = None
            
        scale = self.last_scales.get(tool, 1.0)
        added_item = None
        bw = self.shape_border_width
        
        if tool == "text":
            text, ok = QInputDialog.getMultiLineText(self, "Add Text", "Enter text:")
            if ok and text:
                item = MovableTextItem(text)
                item.type_str = "text"
                item.setScale(scale)
                item.setPos(pos.x(), pos.y())
                self.scene.addItem(item)
                added_item = item
        elif tool == "check":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 15, 12, 25)
            painter.drawLine(12, 25, 28, 5)
            painter.end()
            
            item = MovablePixmapItem(pixmap, item_type="check")
            item.color = self.mark_color
            item.border_width = bw
            item.setScale(scale)
            rect = item.boundingRect()
            item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
            self.scene.addItem(item)
            added_item = item
        elif tool == "cross":
            pixmap = QPixmap(30, 30)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 5, 25, 25)
            painter.drawLine(25, 5, 5, 25)
            painter.end()
            
            item = MovablePixmapItem(pixmap, item_type="cross")
            item.color = self.mark_color
            item.border_width = bw
            item.setScale(scale)
            rect = item.boundingRect()
            item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
            self.scene.addItem(item)
            added_item = item
        elif tool in ["rect", "circle", "triangle"]:
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if self.shape_filled:
                painter.setBrush(self.mark_color)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                
            if tool == "rect":
                painter.drawRect(5, 5, 50, 50)
            elif tool == "circle":
                painter.drawEllipse(5, 5, 50, 50)
            elif tool == "triangle":
                poly = QPolygonF([QPointF(30, 5), QPointF(55, 55), QPointF(5, 55)])
                painter.drawPolygon(poly)
                
            painter.end()
            item = MovablePixmapItem(pixmap, item_type=tool)
            item.color = self.mark_color
            item.border_width = bw
            item.filled = self.shape_filled
            item.setScale(scale)
            rect = item.boundingRect()
            item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
            self.scene.addItem(item)
            added_item = item
        elif tool == "line":
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            pen = QPen(self.mark_color, bw)
            painter.setPen(pen)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawLine(5, 30, 55, 30)
            painter.end()
            item = MovablePixmapItem(pixmap, item_type=tool)
            item.color = self.mark_color
            item.border_width = bw
            item.setScale(scale)
            rect = item.boundingRect()
            item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
            self.scene.addItem(item)
            added_item = item
        elif tool == "image":
            file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                pixmap = QPixmap(file_path)
                if pixmap.width() > 300:
                    pixmap = pixmap.scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
                item = MovablePixmapItem(pixmap, img_path=file_path, item_type="image")
                item.setScale(scale)
                rect = item.boundingRect()
                item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
                self.scene.addItem(item)
                added_item = item
        elif tool == "signature":
            pixmap = QPixmap(self.signature_path)
            if pixmap.width() > 200:
                pixmap = pixmap.scaledToWidth(200, Qt.TransformationMode.SmoothTransformation)
            item = MovablePixmapItem(pixmap, img_path=self.signature_path, item_type="signature")
            item.setScale(scale)
            rect = item.boundingRect()
            item.setPos(pos.x() - (rect.width()*scale) / 2, pos.y() - (rect.height()*scale) / 2)
            self.scene.addItem(item)
            added_item = item
            
        if added_item:
            self.scene.clearSelection()
            added_item.setSelected(True)

    def add_text(self):
        if not self.doc: return
        self.set_tool("text")

    def add_check(self):
        if not self.doc: return
        self.set_tool("check")

    def add_cross(self):
        if not self.doc: return
        self.set_tool("cross")

    def add_rect(self):
        if not self.doc: return
        self.set_tool("rect")

    def add_circle(self):
        if not self.doc: return
        self.set_tool("circle")

    def add_triangle(self):
        if not self.doc: return
        self.set_tool("triangle")

    def add_line(self):
        if not self.doc: return
        self.set_tool("line")

    def add_brush(self):
        if not self.doc: return
        self.set_tool("brush")

    def start_drawing(self, pos):
        self.is_drawing = True
        self.current_drawing_points = [pos]
        self.current_drawing_path = QGraphicsPathItem()
        pen = QPen(self.mark_color, self.shape_border_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.current_drawing_path.setPen(pen)
        self.scene.addItem(self.current_drawing_path)
        path = QPainterPath(pos)
        self.current_drawing_path.setPath(path)

    def continue_drawing(self, pos):
        self.current_drawing_points.append(pos)
        path = self.current_drawing_path.path()
        path.lineTo(pos)
        self.current_drawing_path.setPath(path)

    def finish_drawing(self):
        self.is_drawing = False
        if not self.current_drawing_path: return
        
        path = self.current_drawing_path.path()
        self.scene.removeItem(self.current_drawing_path)
        self.current_drawing_path = None
        
        if len(self.current_drawing_points) < 2:
            return
            
        rect = path.boundingRect()
        bw = self.shape_border_width
        pad = bw + 2
        
        w = int(rect.width() + pad*2) if rect.width() > 0 else 60
        h = int(rect.height() + pad*2) if rect.height() > 0 else 60
        
        pixmap = QPixmap(w, h)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        pen = QPen(self.mark_color, bw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        translated_path = QPainterPath()
        local_points = []
        for i, pt in enumerate(self.current_drawing_points):
            lx = pt.x() - rect.x() + pad
            ly = pt.y() - rect.y() + pad
            local_points.append((lx, ly))
            if i == 0:
                translated_path.moveTo(lx, ly)
            else:
                translated_path.lineTo(lx, ly)
                
        painter.drawPath(translated_path)
        painter.end()
        
        item = MovablePixmapItem(pixmap, item_type="brush")
        item.color = self.mark_color
        item.border_width = bw
        item.drawing_points = local_points
        item.setPos(rect.x() - pad, rect.y() - pad)
        self.scene.addItem(item)
        self.scene.clearSelection()
        item.setSelected(True)
        
        self.current_tool = None
        self.view.setCursor(Qt.CursorShape.ArrowCursor)

    def toggle_filled(self):
        self.shape_filled = not self.shape_filled
        self.btn_filled.setText("🟩 Fill: ON" if self.shape_filled else "🟩 Fill: OFF")
        if self.ghost_item and self.current_tool in ["rect", "circle", "triangle"]:
            current = self.current_tool
            self.set_tool(current)

    def set_mark_color(self):
        color = QColorDialog.getColor(self.mark_color, self, "Select Mark Color")
        if color.isValid():
            self.mark_color = color
            if self.ghost_item and self.current_tool in ["check", "cross", "rect", "circle", "triangle"]:
                current = self.current_tool
                self.set_tool(current)

    def add_image(self):
        if not self.doc: return
        self.set_tool("image")

    def set_signature(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Signature Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            pixmap = QPixmap(file_path)
            pixmap.save(self.signature_path)
            QMessageBox.information(self, "Success", "Signature image updated.")

    def add_signature(self):
        if not self.doc: return
        if not os.path.exists(self.signature_path):
            QMessageBox.warning(self, "Warning", "No signature found. Please set a signature first.")
            return
        self.set_tool("signature")

    def on_scroll_changed(self):
        if not self.doc or not self.page_rects:
            return
        
        # Determine the y-coordinate at the center of the view
        view_center = self.view.viewport().rect().center()
        scene_y = self.view.mapToScene(view_center).y()
        
        current_page = 1
        for rect in self.page_rects:
            if rect['start_y'] <= scene_y <= (rect['start_y'] + rect['height']):
                current_page = rect['page_num'] + 1
                break
                
        total_pages = len(self.doc)
        self.lbl_page_info.setText(f" Page: {current_page} / {total_pages} ")

    def delete_current_page(self):
        if not self.doc or len(self.doc) <= 1:
            QMessageBox.warning(self, "Warning", "Cannot delete the only page in the document.")
            return
            
        view_center = self.view.viewport().rect().center()
        scene_y = self.view.mapToScene(view_center).y()
        
        page_to_delete = 0
        for rect in self.page_rects:
            if rect['start_y'] <= scene_y <= (rect['start_y'] + rect['height']):
                page_to_delete = rect['page_num']
                break
                
        reply = QMessageBox.question(self, "Delete Page", f"Are you sure you want to delete page {page_to_delete + 1}?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            # We need to save the current state, but we MUST modify the y positions of items
            state_json = self.get_state()
            state = json.loads(state_json)
            
            deleted_rect = self.page_rects[page_to_delete]
            height_to_shift = deleted_rect['height'] + 20 # 20 is the spacing
            
            new_items = []
            for item in state.get('items', []):
                y = item['y']
                if y < deleted_rect['start_y']:
                    new_items.append(item)
                elif y > (deleted_rect['start_y'] + deleted_rect['height']):
                    item['y'] = y - height_to_shift
                    new_items.append(item)
                # items inside the deleted page are dropped

            state['items'] = new_items
            modified_state_json = json.dumps(state)

            temp_doc = fitz.open("pdf", self.original_pdf_bytes)
            temp_doc.delete_page(page_to_delete)
            self.original_pdf_bytes = temp_doc.tobytes()
            self.doc = fitz.open("pdf", self.original_pdf_bytes)
            
            self.load_pdf()
            self.restore_state(modified_state_json)
            self.on_scroll_changed()

    def insert_pdf(self):
        if not self.doc: return
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF to Insert", "", "PDF Files (*.pdf)")
        if not file_path: return
            
        total_pages = len(self.doc)
        view_center = self.view.viewport().rect().center()
        scene_y = self.view.mapToScene(view_center).y()
        
        current_page = 0
        for rect in self.page_rects:
            if rect['start_y'] <= scene_y <= (rect['start_y'] + rect['height']):
                current_page = rect['page_num']
                break
                
        insert_after, ok = QInputDialog.getInt(self, "Insert PDF", "Insert after page number (0 for beginning):", current_page + 1, 0, total_pages)
        
        if ok:
            insert_idx = insert_after
            
            with open(file_path, "rb") as f:
                insert_bytes = f.read()
            insert_doc = fitz.open("pdf", insert_bytes)
            num_inserted_pages = len(insert_doc)
            
            # Save state
            state_json = self.get_state()
            state = json.loads(state_json)
            
            temp_doc = fitz.open("pdf", self.original_pdf_bytes)
            
            temp_doc.insert_pdf(insert_doc, start_at=insert_idx)
            
            # Shift items down
            shift_y = 0
            if insert_idx < len(self.page_rects):
                shift_y = self.page_rects[insert_idx]['start_y']
            else:
                shift_y = float('inf') # Nothing to shift
                
            height_to_shift = 0
            for i in range(num_inserted_pages):
                height_to_shift += insert_doc[i].rect.height * PDF_ZOOM + 20
            
            for item in state.get('items', []):
                if item['y'] >= shift_y:
                    item['y'] += height_to_shift
                    
            modified_state_json = json.dumps(state)
            
            self.original_pdf_bytes = temp_doc.tobytes()
            self.doc = fitz.open("pdf", self.original_pdf_bytes)
            
            self.load_pdf()
            self.restore_state(modified_state_json)
            self.on_scroll_changed()

    def add_blank_page(self):
        if not self.doc: return
        
        total_pages = len(self.doc)
        view_center = self.view.viewport().rect().center()
        scene_y = self.view.mapToScene(view_center).y()
        
        current_page = 0
        for rect in self.page_rects:
            if rect['start_y'] <= scene_y <= (rect['start_y'] + rect['height']):
                current_page = rect['page_num']
                break
                
        insert_after, ok = QInputDialog.getInt(self, "Add Blank Page", "Insert after page number (0 for beginning):", current_page + 1, 0, total_pages)
        
        if ok:
            insert_idx = insert_after
            
            # Save state
            state_json = self.get_state()
            state = json.loads(state_json)
            
            temp_doc = fitz.open("pdf", self.original_pdf_bytes)
            
            # determine width and height from the previous page, or first page
            ref_page_idx = insert_idx - 1 if insert_idx > 0 else 0
            if ref_page_idx < len(temp_doc):
                w, h = temp_doc[ref_page_idx].rect.width, temp_doc[ref_page_idx].rect.height
            else:
                w, h = 595.0, 842.0 # A4
                
            temp_doc.new_page(pno=insert_idx, width=w, height=h)
            
            # Shift items down
            shift_y = 0
            if insert_idx < len(self.page_rects):
                shift_y = self.page_rects[insert_idx]['start_y']
            else:
                shift_y = float('inf') # Nothing to shift
                
            height_to_shift = (h * PDF_ZOOM) + 20
            
            for item in state.get('items', []):
                if item['y'] >= shift_y:
                    item['y'] += height_to_shift
                    
            modified_state_json = json.dumps(state)
            
            self.original_pdf_bytes = temp_doc.tobytes()
            self.doc = fitz.open("pdf", self.original_pdf_bytes)
            
            self.load_pdf()
            self.restore_state(modified_state_json)
            self.on_scroll_changed()

    def get_page_for_y(self, y_pos):
        for rect in self.page_rects:
            if rect['start_y'] <= y_pos <= (rect['start_y'] + rect['height']):
                return rect
        return None

    def get_state(self):
        items_data = []
        for item in self.scene.items():
            if item in self.pdf_bg_items: continue
            if item == self.ghost_item: continue
            
            pos = item.scenePos()
            scale = item.scale()
            rot = item.rotation()
            if isinstance(item, MovableTextItem):
                c = item.defaultTextColor()
                items_data.append({
                    "type": "text", "text": item.toPlainText(),
                    "x": pos.x(), "y": pos.y(), "scale": scale, "rotation": rot,
                    "color": [c.red(), c.green(), c.blue()],
                    "font_size": item.font_size,
                    "letter_spacing": item.letter_spacing
                })
            elif isinstance(item, MovablePixmapItem):
                c = getattr(item, 'color', Qt.GlobalColor.black)
                if isinstance(c, QColor): c_val = [c.red(), c.green(), c.blue()]
                else: c_val = [0,0,0]
                
                scale_x = getattr(item, 'scale_x', scale)
                scale_y = getattr(item, 'scale_y', scale)
                
                data = {
                    "type": item.type_str,
                    "x": pos.x(), "y": pos.y(), "scale": scale, "scale_x": scale_x, "scale_y": scale_y, "rotation": rot,
                    "color": c_val,
                    "filled": getattr(item, 'filled', False),
                    "border_width": getattr(item, 'border_width', 3)
                }
                
                if item.type_str == "brush" and hasattr(item, 'drawing_points'):
                    data["drawing_points"] = item.drawing_points
                
                if item.type_str in ["image", "signature"]:
                    img = item.pixmap().toImage()
                    ba = QByteArray()
                    buf = QBuffer(ba)
                    buf.open(QIODevice.OpenModeFlag.WriteOnly)
                    img.save(buf, "PNG")
                    data["b64_png"] = base64.b64encode(ba.data()).decode("utf-8")
                
                items_data.append(data)
        return json.dumps({"items": items_data})

    def restore_state(self, json_str):
        try:
            data = json.loads(json_str)
            for item_data in data.get("items", []):
                t = item_data["type"]
                x = item_data["x"]
                y = item_data["y"]
                scale = item_data.get("scale", 1.0)
                scale_x = item_data.get("scale_x", scale)
                scale_y = item_data.get("scale_y", scale)
                rot = item_data.get("rotation", 0.0)
                
                if t == "text":
                    item = MovableTextItem(item_data["text"], font_size=item_data.get("font_size", 16), letter_spacing=item_data.get("letter_spacing", 0.0))
                    color_arr = item_data.get("color", [0,0,0])
                    item.setDefaultTextColor(QColor(color_arr[0], color_arr[1], color_arr[2]))
                    item.setScale(scale)
                    item.setPos(x, y)
                    item.setTransformOriginPoint(item.boundingRect().center())
                    item.setRotation(rot)
                    self.scene.addItem(item)
                else:
                    color_arr = item_data.get("color", [0,0,0])
                    qcolor = QColor(color_arr[0], color_arr[1], color_arr[2])
                    
                    if t in ["image", "signature"]:
                        b64 = item_data.get("b64_png", "")
                        if b64:
                            ba = QByteArray(base64.b64decode(b64))
                            img = QImage()
                            img.loadFromData(ba, "PNG")
                            pixmap = QPixmap.fromImage(img)
                            item = MovablePixmapItem(pixmap, item_type=t)
                            item.color = qcolor
                            item.setScaleXY(scale_x, scale_y)
                            item.setPos(x, y)
                            item.setTransformOriginPoint(item.boundingRect().center())
                            item.setRotation(rot)
                            self.scene.addItem(item)
                    else:
                        item = MovablePixmapItem(QPixmap(), item_type=t)
                        item.color = qcolor
                        item.filled = item_data.get("filled", False)
                        item.border_width = item_data.get("border_width", 3)
                        item.redraw()
                        item.setScaleXY(scale_x, scale_y)
                        item.setPos(x, y)
                        item.setTransformOriginPoint(item.boundingRect().center())
                        item.setRotation(rot)
                        self.scene.addItem(item)
        except Exception as e:
            logger.error("Failed to restore state", exc_info=True)

    def edit_pdf(self):
        if not self.doc: return
        
        reply = QMessageBox.question(self, "Edit PDF", 
            "Convert all text and images in the current PDF into editable elements? "
            "(This cannot be easily undone until saved/reloaded without saving)", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
        if reply != QMessageBox.StandardButton.Yes:
            return

        temp_doc = fitz.open("pdf", self.original_pdf_bytes)
        
        for page_num in range(len(temp_doc)):
            page = temp_doc[page_num]
            rect_info = self.page_rects[page_num]
            start_y = rect_info['start_y']
            
            # Extract texts
            text_data = page.get_text("dict")
            for block in text_data.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if not text: continue
                            
                            bbox = span["bbox"] # (x0, y0, x1, y1)
                            font_size = span["size"]
                            color_int = span["color"]
                            
                            b = color_int & 255
                            g = (color_int >> 8) & 255
                            r = (color_int >> 16) & 255
                            
                            page.add_redact_annot(bbox, cross_out=False)
                            
                            item = MovableTextItem(text, font_size=font_size)
                            item.setDefaultTextColor(QColor(r, g, b))
                            
                            scene_x = bbox[0] * PDF_ZOOM
                            scene_y = start_y + bbox[1] * PDF_ZOOM
                            item.setPos(scene_x, scene_y)
                            
                            item.setScale(PDF_ZOOM / (96.0 / 72.0))
                            self.scene.addItem(item)
            
            # Extract images
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                base_image = temp_doc.extract_image(xref)
                if base_image:
                    image_bytes = base_image["image"]
                    rects = page.get_image_rects(xref)
                    if rects:
                        bbox = rects[0]
                        page.add_redact_annot(bbox, cross_out=False)
                        
                        ba = QByteArray(image_bytes)
                        qimg = QImage()
                        qimg.loadFromData(ba)
                        pixmap = QPixmap.fromImage(qimg)
                        item = MovablePixmapItem(pixmap, item_type="image")
                        
                        scene_x = bbox[0] * PDF_ZOOM
                        scene_y = start_y + bbox[1] * PDF_ZOOM
                        item.setPos(scene_x, scene_y)
                        
                        scale_x = (bbox[2] - bbox[0]) * PDF_ZOOM / pixmap.width()
                        scale_y = (bbox[3] - bbox[1]) * PDF_ZOOM / pixmap.height()
                        item.setScale(max(scale_x, scale_y))
                        self.scene.addItem(item)
            
            # Apply redactions for text and images first so they aren't captured in the vector graphic pixmaps
            page.apply_redactions(images=2)
            
            # Extract vector graphics (paths)
            drawings = page.get_drawings()
            if drawings:
                valid_rects = []
                page_area = page.rect.get_area()
                for d in drawings:
                    r = d["rect"]
                    if r.get_area() < page_area * 0.5:
                        valid_rects.append(r)
                
                merged = True
                while merged:
                    merged = False
                    new_rects = []
                    while valid_rects:
                        r1 = valid_rects.pop(0)
                        merged_r1 = False
                        for i, r2 in enumerate(new_rects):
                            r2_exp = fitz.Rect(r2.x0 - 2, r2.y0 - 2, r2.x1 + 2, r2.y1 + 2)
                            if r1.intersects(r2_exp):
                                new_rects[i] = r2 | r1
                                merged_r1 = True
                                merged = True
                                break
                        if not merged_r1:
                            new_rects.append(r1)
                    valid_rects = new_rects

                mat = fitz.Matrix(PDF_ZOOM, PDF_ZOOM)
                for bbox in valid_rects:
                    pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=True, annots=False)
                    if pix.width > 0 and pix.height > 0:
                        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(img)
                        item = MovablePixmapItem(pixmap, item_type="image")
                        
                        scene_x = bbox.x0 * PDF_ZOOM
                        scene_y = start_y + bbox.y0 * PDF_ZOOM
                        item.setPos(scene_x, scene_y)
                        item.setScale(1.0)
                        self.scene.addItem(item)
                        
                        page.add_redact_annot(bbox, cross_out=False)
                
            page.apply_redactions(images=2)
        
        self.original_pdf_bytes = temp_doc.tobytes()
        self.doc = fitz.open("pdf", self.original_pdf_bytes)
        
        mat = fitz.Matrix(PDF_ZOOM, PDF_ZOOM)
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self.pdf_bg_items[page_num].setPixmap(pixmap)

    def _build_save_filename(self):
        """Build a suggested filename with suffixes based on modifications."""
        base = self.original_filename if self.original_filename else ""
        if not base:
            return ""
        
        has_modifications = False
        has_signature = False
        
        for item in self.scene.items():
            if item in self.pdf_bg_items:
                continue
            if item == self.ghost_item:
                continue
            # Any user-added element counts as a modification
            if isinstance(item, (MovableTextItem, MovablePixmapItem)):
                has_modifications = True
                if isinstance(item, MovablePixmapItem) and item.type_str == "signature":
                    has_signature = True
        
        suffix = ""
        if has_modifications:
            suffix += "_M"
        if has_signature:
            suffix += "S"
        
        return base + suffix + ".pdf"

    def save_pdf(self):
        if not self.doc: return
        
        suggested_name = self._build_save_filename()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", suggested_name, "PDF Files (*.pdf)")
        if not file_path: return
        
        # Open a fresh copy of the original PDF bytes so we don't permanently bake items into our live viewer
        out_doc = fitz.open("pdf", self.original_pdf_bytes)
        
        for item in self.scene.items():
            if item in self.pdf_bg_items:
                continue
            if item == self.ghost_item:
                continue
                
            pos = item.scenePos()
            page_info = self.get_page_for_y(pos.y())
            
            if not page_info:
                continue # item is outside any page bounds
                
            page_num = page_info['page_num']
            start_y = page_info['start_y']
            
            page = out_doc[page_num]
            
            # Convert qt scene coordinates to pdf coordinates
            pdf_x = pos.x() / PDF_ZOOM
            pdf_y = (pos.y() - start_y) / PDF_ZOOM
            
            if isinstance(item, MovableTextItem):
                text = item.toPlainText()
                color = item.defaultTextColor()
                r, g, b, _ = color.getRgbF()
                fitz_color = (r, g, b)
                pdf_font_size = (item.font_size * item.scale()) / PDF_ZOOM * 1.33 
                
                rect = item.boundingRect()
                scaled_height = rect.height() * item.scale()
                pdf_y_insert = pdf_y + (scaled_height / PDF_ZOOM) * 0.75
                
                rot = item.rotation()
                morph = None
                if rot != 0:
                    cx = pdf_x + (rect.width() * item.scale() / 2) / PDF_ZOOM
                    cy = pdf_y + (rect.height() * item.scale() / 2) / PDF_ZOOM
                    morph = (fitz.Point(cx, cy), fitz.Matrix(-rot))
                
                if item.letter_spacing == 0.0:
                    page.insert_text(fitz.Point(pdf_x, pdf_y_insert), text, fontsize=pdf_font_size, color=fitz_color, morph=morph)
                else:
                    current_x = pdf_x
                    spacing_pdf = item.letter_spacing * item.scale() / PDF_ZOOM
                    for char in text:
                        page.insert_text(fitz.Point(current_x, pdf_y_insert), char, fontsize=pdf_font_size, color=fitz_color, morph=morph)
                        char_width = fitz.get_text_length(char, fontname="helv", fontsize=pdf_font_size)
                        current_x += char_width + spacing_pdf
            
            elif isinstance(item, MovablePixmapItem):
                scale_x = getattr(item, 'scale_x', item.scale())
                scale_y = getattr(item, 'scale_y', item.scale())
                if item.type_str in ["rect", "circle", "triangle", "line"]:
                    fitz_color = (item.color.redF(), item.color.greenF(), item.color.blueF())
                    fill_color = fitz_color if item.filled else None
                    width = getattr(item, 'border_width', 3) / PDF_ZOOM
                    
                    inner_x = pdf_x + (5 * scale_x / PDF_ZOOM)
                    inner_y = pdf_y + (5 * scale_y / PDF_ZOOM)
                    inner_w = 50 * scale_x / PDF_ZOOM
                    inner_h = 50 * scale_y / PDF_ZOOM
                    inner_rect = fitz.Rect(inner_x, inner_y, inner_x + inner_w, inner_y + inner_h)
                    
                    rot = item.rotation()
                    morph = None
                    if rot != 0:
                        cx = pdf_x + (30 * scale_x) / PDF_ZOOM
                        cy = pdf_y + (30 * scale_y) / PDF_ZOOM
                        morph = (fitz.Point(cx, cy), fitz.Matrix(-rot))
                    
                    if item.type_str == "rect":
                        page.draw_rect(inner_rect, color=fitz_color, fill=fill_color, width=width, morph=morph)
                    elif item.type_str == "circle":
                        page.draw_oval(inner_rect, color=fitz_color, fill=fill_color, width=width, morph=morph)
                    elif item.type_str == "triangle":
                        p1 = fitz.Point(inner_rect.x0 + inner_w / 2, inner_rect.y0)
                        p2 = fitz.Point(inner_rect.x1, inner_rect.y1)
                        p3 = fitz.Point(inner_rect.x0, inner_rect.y1)
                        page.draw_polygon([p1, p2, p3], color=fitz_color, fill=fill_color, width=width, morph=morph)
                    elif item.type_str == "line":
                        p1 = fitz.Point(pdf_x + (5 * scale_x / PDF_ZOOM), pdf_y + (30 * scale_y / PDF_ZOOM))
                        p2 = fitz.Point(pdf_x + (55 * scale_x / PDF_ZOOM), pdf_y + (30 * scale_y / PDF_ZOOM))
                        page.draw_line(p1, p2, color=fitz_color, width=width, morph=morph)
                elif item.type_str == "brush" and hasattr(item, 'drawing_points'):
                    fitz_color = (item.color.redF(), item.color.greenF(), item.color.blueF())
                    width = getattr(item, 'border_width', 3) / PDF_ZOOM
                    
                    pdf_points = []
                    for px, py in item.drawing_points:
                        pdf_px = pdf_x + (px * scale_x / PDF_ZOOM)
                        pdf_py = pdf_y + (py * scale_y / PDF_ZOOM)
                        pdf_points.append(fitz.Point(pdf_px, pdf_py))
                        
                    rot = item.rotation()
                    morph = None
                    if rot != 0:
                        orig_rect = item.boundingRect()
                        cx = pdf_x + (orig_rect.width() * scale_x / 2) / PDF_ZOOM
                        cy = pdf_y + (orig_rect.height() * scale_y / 2) / PDF_ZOOM
                        morph = (fitz.Point(cx, cy), fitz.Matrix(-rot))
                        
                    if len(pdf_points) > 1:
                        page.draw_polyline(pdf_points, color=fitz_color, width=width, morph=morph)
                else:
                    img = item.pixmap().toImage()
                    rot = item.rotation()
                    if rot != 0:
                        trans = QTransform().rotate(rot)
                        img = img.transformed(trans, Qt.TransformationMode.SmoothTransformation)
                    
                    pdf_w = (img.width() * scale_x) / PDF_ZOOM
                    pdf_h = (img.height() * scale_y) / PDF_ZOOM
                    
                    orig_rect = item.boundingRect()
                    scaled_orig_w = orig_rect.width() * scale_x
                    scaled_orig_h = orig_rect.height() * scale_y
                    center_x = pdf_x + (scaled_orig_w / 2) / PDF_ZOOM
                    center_y = pdf_y + (scaled_orig_h / 2) / PDF_ZOOM
                    
                    pdf_rect = fitz.Rect(center_x - pdf_w/2, center_y - pdf_h/2, center_x + pdf_w/2, center_y + pdf_h/2)
                    
                    if item.img_path and rot == 0:
                        page.insert_image(pdf_rect, filename=item.img_path)
                    else:
                        byte_array = QByteArray()
                        buffer = QBuffer(byte_array)
                        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                        img.save(buffer, "PNG")
                        page.insert_image(pdf_rect, stream=byte_array.data())

        state_json = self.get_state()
        out_doc.embfile_add("original_pdf", self.original_pdf_bytes, filename="original.pdf")
        out_doc.embfile_add("editor_state", state_json.encode("utf-8"), filename="state.json")
        out_doc.save(file_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFEditor()
    window.showMaximized()
    sys.exit(app.exec())
