"""
Documentation Page - Read inline docs about NitroSense
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QTextEdit, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import markdown
from nitrosense.core.logger import logger


class DocsPage(QWidget):
    """Documentation viewer integrated into main app."""
    
    def __init__(self, system=None):
        super().__init__()
        self.system = system
        self.docs_dir = self._find_docs_dir()
        self.current_doc = None
        
        logger.info(f"DocsPage initialized, docs_dir={self.docs_dir}")
        self.setup_ui()
        self._load_docs_list()
    
    def setup_ui(self):
        """Setup UI layout with sidebar + content area."""
        layout = QHBoxLayout(self)
        
        # Sidebar: List of documents
        sidebar_layout = QVBoxLayout()
        
        # Title
        title = QFont("Segoe UI", 12, QFont.Weight.Bold)
        title_label = QTextEdit()
        title_label.setFont(title)
        title_label.setText("Documentation")
        title_label.setReadOnly(True)
        title_label.setMaximumHeight(50)
        title_label.setStyleSheet("background-color: #2a2a2a; color: #007aff; border: none;")
        sidebar_layout.addWidget(title_label)
        
        # Docs list
        self.docs_list = QListWidget()
        self.docs_list.itemClicked.connect(self._on_doc_selected)
        self.docs_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 14px;
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #007aff;
                color: white;
                border-radius: 10px;
            }
        """)
        sidebar_layout.addWidget(self.docs_list)
        
        # Tutorials section
        tutorial_label = QTextEdit()
        tutorial_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        tutorial_label.setText("Interactive Tutorials")
        tutorial_label.setReadOnly(True)
        tutorial_label.setMaximumHeight(40)
        tutorial_label.setStyleSheet("background-color: #2a2a2a; color: #00d1ff; border: none; padding: 5px;")
        sidebar_layout.addWidget(tutorial_label)
        
        self.tutorial_list = QListWidget()
        self.tutorial_list.itemClicked.connect(self._on_tutorial_selected)
        self.tutorial_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 14px;
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #00d1ff;
                color: white;
                border-radius: 10px;
            }
        """)
        sidebar_layout.addWidget(self.tutorial_list)
        
        # Load tutorials
        self._load_tutorials()
        
        # Sidebar container
        sidebar_container = QWidget()
        sidebar_container.setLayout(sidebar_layout)
        sidebar_container.setMaximumWidth(250)
        
        # Main content area
        content_layout = QVBoxLayout()
        
        # Document viewer
        self.doc_viewer = QTextEdit()
        self.doc_viewer.setReadOnly(True)
        self.doc_viewer.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                padding: 20px;
                border: 1px solid #333;
                border-radius: 16px;
                font-family: 'Segoe UI', monospace;
                font-size: 11pt;
            }
        """)
        content_layout.addWidget(self.doc_viewer)
        
        # Back button
        btn_layout = QHBoxLayout()
        btn_back = QPushButton("← Back")
        btn_back.clicked.connect(self._select_first_doc)
        btn_back.setMaximumWidth(100)
        btn_back.setStyleSheet(
            "QPushButton { border-radius: 12px; padding: 8px 12px; }"
        )
        btn_layout.addStretch()
        btn_layout.addWidget(btn_back)
        content_layout.addLayout(btn_layout)
        
        # Content container
        content_container = QWidget()
        content_container.setLayout(content_layout)
        
        # Add to main layout
        layout.addWidget(sidebar_container, 1)
        layout.addWidget(content_container, 2)
        
        self.setLayout(layout)
    
    def _find_docs_dir(self):
        """Locate the documentation folder from the package root."""
        current_file = Path(__file__).resolve()
        package_docs = current_file.parents[2] / "docs"  # nitrosense/docs
        repo_docs = None

        if len(current_file.parents) >= 5:
            repo_docs = current_file.parents[4] / "DOCS"

        if package_docs.exists():
            return package_docs
        if repo_docs and repo_docs.exists():
            return repo_docs

        return package_docs

    def _load_docs_list(self):
        """Load documentation files from docs/ folder."""
        if not self.docs_dir.exists():
            logger.warning(f"Docs directory not found: {self.docs_dir}")
            self.doc_viewer.setText("Documentation folder not found")
            return
        
        # Get all .md files sorted by name
        md_files = sorted(self.docs_dir.glob("*.md"))
        
        if not md_files:
            logger.warning("No markdown docs found")
            self.doc_viewer.setText("No documentation files found")
            return
        
        for md_file in md_files:
            # Extract title from filename
            # 01-quickstart.md → Quick Start
            title = md_file.stem.split("-", 1)[1].replace("-", " ").title()
            
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, md_file)
            self.docs_list.addItem(item)
        
        # Select first doc
        self._select_first_doc()
    
    def _select_first_doc(self):
        """Select and display first documentation."""
        if self.docs_list.count() > 0:
            self.docs_list.setCurrentRow(0)
            self._on_doc_selected(self.docs_list.item(0))
    
    def _on_doc_selected(self, item: QListWidgetItem):
        """Load and display selected documentation."""
        if item is None:
            return
        
        md_path = item.data(Qt.ItemDataRole.UserRole)
        
        try:
            # Read markdown file
            content = md_path.read_text(encoding='utf-8')
            
            # Convert markdown to HTML
            html_content = markdown.markdown(
                content,
                extensions=['tables', 'fenced_code', 'codehilite']
            )
            
            # Apply styling
            styled_html = self._style_html(html_content)
            
            # Display in viewer
            self.doc_viewer.setHtml(styled_html)
            self.current_doc = md_path
            
            logger.info(f"Loaded doc: {md_path.name}")
            
        except Exception as e:
            logger.error(f"Failed to load doc {md_path.name}: {e}")
            self.doc_viewer.setText(f"Error loading {md_path.name}\n\n{str(e)}")
    
    def _style_html(self, html_content: str) -> str:
        """Apply dark theme styling to HTML."""
        dark_css = """
        <style>
        body {
            background-color: #1e1e1e;
            color: #e0e0e0;
            font-family: 'Segoe UI', sans-serif;
            line-height: 1.6;
            padding: 20px;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #007aff;
            margin-top: 20px;
            margin-bottom: 10px;
            border-bottom: 1px solid #333;
            padding-bottom: 8px;
        }
        h1 { font-size: 24pt; }
        h2 { font-size: 20pt; }
        h3 { font-size: 16pt; }
        
        a {
            color: #007aff;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
        
        code {
            background-color: #2a2a2a;
            color: #34c759;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', monospace;
        }
        
        pre {
            background-color: #2a2a2a;
            border-left: 3px solid #007aff;
            padding: 12px;
            overflow-x: auto;
            border-radius: 5px;
        }
        
        pre code {
            background-color: transparent;
            color: #34c759;
            padding: 0;
        }
        
        blockquote {
            border-left: 4px solid #ff9500;
            margin-left: 0;
            padding-left: 16px;
            color: #ff9500;
        }
        
        table {
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }
        
        table th {
            background-color: #2a2a2a;
            color: #007aff;
            padding: 10px;
            text-align: left;
            border: 1px solid #333;
        }
        
        table td {
            padding: 8px;
            border: 1px solid #333;
        }
        
        table tr:hover {
            background-color: #252525;
        }
        
        ul, ol {
            margin-left: 20px;
        }
        
        li {
            margin: 5px 0;
        }
        
        strong {
            color: #007aff;
        }
        
        em {
            color: #ff9500;
        }
        </style>
        """
        
        return dark_css + html_content
    
    def _load_tutorials(self):
        """Load interactive tutorials."""
        tutorials = [
            ("Getting Started", "intro"),
            ("Monitoring Temperatures", "monitoring"),
            ("Fan Control Basics", "fan_control"),
            ("Configuration Guide", "config"),
            ("Troubleshooting", "troubleshooting"),
        ]
        
        for title, tutorial_id in tutorials:
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, tutorial_id)
            self.tutorial_list.addItem(item)
    
    def _on_tutorial_selected(self, item: QListWidgetItem):
        """Handle tutorial selection."""
        tutorial_id = item.data(Qt.ItemDataRole.UserRole)
        
        tutorial_content = self._get_tutorial_content(tutorial_id)
        self.doc_viewer.setHtml(self._style_html(tutorial_content))
    
    def _get_tutorial_content(self, tutorial_id: str) -> str:
        """Get tutorial content by ID."""
        tutorials = {
            "intro": """
# Welcome to NitroSense Ultimate!

## Getting Started Tutorial

### Step 1: Understanding the Interface
NitroSense Ultimate has 5 main pages:
- **Home**: Temperature monitoring and controls
- **Status**: System health indicators  
- **Config**: Thermal curve and settings
- **Labs**: Advanced testing and diagnostics
- **Docs**: This documentation

### Step 2: First Run
1. The app will start with a splash screen showing initialization
2. Check the Status page for any issues (should be all green)
3. Monitor temperatures on the Home page
4. Adjust fan curves in Config if needed

### Step 3: Basic Controls
- Use the fan slider on Home page for manual control
- Enable/disable AI mode in Config
- Check logs in Labs if you encounter issues

**Next:** Click "Monitoring Temperatures" tutorial
            """,
            
            "monitoring": """
# Temperature Monitoring

## Understanding the Dashboard

### Temperature Display
- Shows current CPU temperature in large digits
- Color changes: Blue (cool) → Yellow (warm) → Red (hot)

### Graph
- Shows temperature history over time
- Useful for spotting trends and spikes
- Can be hidden in Config → Display & Behavior

### Status Indicators
- Green: OK
- Yellow: Warning  
- Red: Critical

## Best Practices
- Keep temperatures below 80°C during gaming
- Watch for sudden spikes (may indicate fan issues)
- Use the graph to tune your fan curves

**Next:** Click "Fan Control Basics" tutorial
            """,
            
            "fan_control": """
# Fan Control Basics

## How Fan Control Works

### Automatic Mode (Recommended)
- AI analyzes temperature patterns
- Adjusts fan speed proactively
- Prevents thermal throttling

### Manual Mode
- Direct fan speed control via slider
- Overrides automatic control
- Useful for testing or custom scenarios

### Fan Curves
- Define speed vs temperature relationships
- Three levels: Low, Mid, High
- Customize in Config page

## Tips
- Start with default curves
- Fine-tune based on your system's behavior
- Monitor fan RPM in Status page

**Next:** Click "Configuration Guide" tutorial
            """,
            
            "config": """
# Configuration Guide

## Main Settings

### Thermal Curves
- **Low**: Idle temperatures (around 50°C)
- **Mid**: Light load (around 65°C)  
- **High**: Heavy load (around 80°C)

### Advanced Options
- **AI Sensitivity**: How aggressive the AI is
- **Hide Graph**: Clean up the interface
- **Start Minimized**: Launch to system tray

### Notifications
- Enable alerts for critical events
- Customize which events to monitor

## Saving Changes
1. Make your adjustments
2. Click "Save Configuration"
3. Restart the app if needed

**Next:** Click "Troubleshooting" tutorial
            """,
            
            "troubleshooting": """
# Troubleshooting Guide

## Common Issues

### High Temperatures
- Check fan curves in Config
- Ensure vents are clear
- Verify NBFC service is running

### App Won't Start
- Check logs in ~/.config/nitrosense/logs/
- Verify Python dependencies
- Run from terminal for error messages

### Fan Not Responding
- Test in Labs → Test NBFC
- Check hardware connections
- Verify EC module loaded

## Getting Help
- Use the "Copy Logs" button on splash screen
- Check Status page for detailed errors
- Visit the Docs page for more info

## Emergency Mode
- If temperatures exceed 95°C, emergency protocols activate
- Fans go to 100%, background processes killed
- Check logs for details

**Tutorial Complete!** 🎉
            """
        }
        
        return tutorials.get(tutorial_id, "# Tutorial not found")
