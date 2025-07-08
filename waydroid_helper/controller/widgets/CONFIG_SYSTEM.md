 # Widget配置系统设计文档

## 概述

新的配置系统为Widget提供了统一、灵活、易于扩展的配置管理方案。它支持多种配置类型、自动UI生成、数据验证和持久化存储。

## 核心组件

### 1. ConfigItem 抽象基类

所有配置项的基类，定义了配置项的基本接口：

```python
class ConfigItem(ABC):
    key: str          # 配置键
    label: str        # 显示标签
    description: str  # 配置说明
    value: Any        # 配置值
    
    def create_ui_widget(self) -> Gtk.Widget    # 创建UI控件
    def get_value_from_ui(self, widget) -> Any  # 从UI获取值
    def set_value_to_ui(self, widget, value)   # 设置值到UI
    def validate(self, value) -> bool          # 验证值
    def serialize(self) -> Dict[str, Any]      # 序列化
```

### 2. 具体配置项类型

#### SliderConfig - 滑动条配置
```python
@dataclass
class SliderConfig(ConfigItem):
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    show_value: bool = True
```

#### DropdownConfig - 下拉选择配置
```python
@dataclass
class DropdownConfig(ConfigItem):
    options: List[str] = field(default_factory=list)
    option_labels: Optional[Dict[str, str]] = None
```

#### TextConfig - 文本输入配置
```python
@dataclass
class TextConfig(ConfigItem):
    placeholder: str = ""
    max_length: int = 0
```

#### SwitchConfig - 开关配置
```python
@dataclass
class SwitchConfig(ConfigItem):
    default_value: bool = False
```

### 3. ConfigManager - 配置管理器

统一管理Widget的所有配置项：

```python
class ConfigManager:
    def add_config(self, config: ConfigItem) -> None
    def set_value(self, key: str, value: Any) -> bool
    def get_value(self, key: str) -> Any
    def add_change_callback(self, key: str, callback: Callable) -> None
    def create_ui_panel(self) -> Gtk.Widget
    def apply_values_from_ui(self) -> bool
    def serialize(self) -> Dict[str, Any]
    def deserialize(self, data: Dict[str, Any]) -> None
```

## 使用方法

### 1. 在Widget中添加配置

```python
class MyWidget(BaseWidget):
    def __init__(self, ...):
        super().__init__(...)
        self.my_setting = 50
        
    def setup_config(self) -> None:
        """设置配置项"""
        super().setup_config()
        
        # 添加滑动条配置
        slider_config = create_slider_config(
            key="my_setting",
            label="My Setting",
            value=self.my_setting,
            min_value=0,
            max_value=100,
            step=5,
            description="This is my setting"
        )
        self.add_config_item(slider_config)
        
        # 添加配置变更回调
        self.add_config_change_callback("my_setting", self._on_my_setting_changed)
    
    def _on_my_setting_changed(self, key: str, value: int) -> None:
        """处理配置变更"""
        self.my_setting = int(value)
        logger.debug(f"My setting changed to: {self.my_setting}")
        self.queue_draw()  # 重绘widget
```

### 2. 支持的配置类型

#### 滑动条配置
```python
slider_config = create_slider_config(
    key="opacity",
    label="Opacity",
    value=80,
    min_value=0,
    max_value=100,
    step=5,
    description="Controls transparency"
)
```

#### 下拉选择配置
```python
dropdown_config = create_dropdown_config(
    key="theme",
    label="Theme",
    value="blue",
    options=["blue", "red", "green"],
    option_labels={
        "blue": "Blue Theme",
        "red": "Red Theme",
        "green": "Green Theme"
    },
    description="Choose color theme"
)
```

#### 文本输入配置
```python
text_config = create_text_config(
    key="display_text",
    label="Display Text",
    value="Hello",
    placeholder="Enter text...",
    max_length=20,
    description="Text to display"
)
```

#### 开关配置
```python
switch_config = create_switch_config(
    key="show_border",
    label="Show Border",
    value=True,
    description="Whether to show border"
)
```

### 3. 配置变更回调

```python
def _on_config_changed(self, key: str, value: Any) -> None:
    """统一的配置变更处理"""
    if key == "opacity":
        self.opacity = int(value)
        self.queue_draw()
    elif key == "theme":
        self.theme = value
        self.queue_draw()
    elif key == "display_text":
        self.display_text = value
        self.queue_draw()
    elif key == "show_border":
        self.show_border = bool(value)
        self.queue_draw()
```

## 系统特性

### 1. 自动UI生成
- 根据配置项类型自动生成相应的UI控件
- 支持滑动条、下拉框、文本输入框、开关等
- 自动布局和样式

### 2. 数据验证
- 每个配置项都有内置的验证逻辑
- 滑动条验证数值范围
- 下拉框验证选项有效性
- 文本框验证长度限制

### 3. 配置持久化
- 支持配置序列化和反序列化
- 与布局保存/加载集成
- JSON格式存储

### 4. 类型安全
- 使用dataclass定义配置项
- 类型提示和验证
- 运行时类型检查

### 5. 向后兼容
- 保留原有API (`get_config`, `set_config`, `add_config_handler`)
- 逐步迁移现有代码
- 不破坏现有功能

## 完整示例

参见 `example_widget.py` 文件，展示了如何使用所有类型的配置项：

```python
class ExampleWidget(BaseWidget):
    def __init__(self, ...):
        super().__init__(...)
        # 配置属性
        self.opacity = 80
        self.color_theme = "blue"
        self.display_text = "Example"
        self.show_border = True
        self.animation_speed = 50
        
    def setup_config(self) -> None:
        super().setup_config()
        
        # 添加各种类型的配置项
        self.add_config_item(create_slider_config(...))
        self.add_config_item(create_dropdown_config(...))
        self.add_config_item(create_text_config(...))
        self.add_config_item(create_switch_config(...))
        
        # 添加配置变更回调
        self.add_config_change_callback("opacity", self._on_opacity_changed)
        # ... 其他回调
```

## 扩展指南

### 1. 添加新的配置类型

```python
@dataclass
class ColorConfig(ConfigItem):
    """颜色选择配置"""
    default_color: str = "#000000"
    
    def create_ui_widget(self) -> Gtk.Widget:
        # 创建颜色选择器
        color_button = Gtk.ColorButton()
        # 设置颜色
        return color_button
    
    def get_value_from_ui(self, widget: Gtk.Widget) -> str:
        # 从颜色选择器获取颜色值
        pass
    
    def validate(self, value: Any) -> bool:
        # 验证颜色值格式
        pass
```

### 2. 自定义配置面板

```python
class CustomConfigManager(ConfigManager):
    def create_ui_panel(self) -> Gtk.Widget:
        # 创建自定义的配置面板布局
        pass
```

## 最佳实践

1. **配置项命名**：使用有意义的key名称，如"opacity"而不是"op"
2. **描述信息**：为每个配置项提供清晰的description
3. **合理分组**：相关的配置项应该在setup_config()中连续添加
4. **验证范围**：设置合适的min/max值和验证逻辑
5. **回调优化**：在回调中只处理必要的更新，避免性能问题
6. **持久化考虑**：确保配置值可以正确序列化和反序列化

## 迁移指南

将现有Widget迁移到新配置系统：

1. 重写`setup_config()`方法，添加配置项
2. 将`get_config()`返回的配置转换为配置项
3. 将`add_config_handler()`调用改为`add_config_change_callback()`
4. 测试配置UI和持久化功能

新配置系统提供了更好的扩展性、类型安全性和用户体验，建议新开发的Widget都使用这个系统。