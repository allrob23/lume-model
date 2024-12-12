"""
This module contains definitions of LUME-model variables for use with lume tools.
Variables are designed as pure descriptors and thus aren't intended to hold actual values,
but they can be used to validate encountered values.

For now, only scalar floating-point variables are supported.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

import numpy as np
from pydantic import BaseModel, field_validator, model_validator, ConfigDict


class Variable(BaseModel, ABC):
    """Abstract variable base class.

    Attributes:
        name: Name of the variable.
    """
    name: str

    @property
    @abstractmethod
    def default_validation_config(self) -> dict[str, bool]:
        """Determines default behavior during validation."""
        return {}

    @abstractmethod
    def validate_value(self, value: Any, config: dict[str, bool] = None):
        pass

    def model_dump(self, **kwargs) -> dict[str, Any]:
        config = super().model_dump(**kwargs)
        return {"variable_class": self.__class__.__name__} | config


class ScalarVariable(Variable):
    """Variable for float values.

    Attributes:
        default_value: Default value for the variable.
        value_range: Value range that is considered valid for the variable. If the value range is set to None,
          the variable is interpreted as a constant and values are validated against the default value.
        value_range_tolerance: Absolute tolerance when checking whether values are within the valid range.
        unit: Unit associated with the variable.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    default_value: float
    value_range: Optional[tuple[float, float]] = None
    value_range_tolerance: Optional[float] = 1e-8
    unit: Optional[str] = None

    @field_validator("value_range", mode="before")
    @classmethod
    def validate_value_range(cls, value):
        if value is not None:
            value = tuple(value)
            if not value[0] <= value[1]:
                raise ValueError(f"Minimum value ({value[0]}) must be lower or equal than maximum ({value[1]}).")
        return value

    @model_validator(mode="after")
    def validate_default_value(self):
        if self.default_value is not None and self.value_range is not None:
            if not self._value_is_within_range(self.default_value):
                raise ValueError(
                    "Default value ({}) is out of valid range "
                    "([{},{}]).".format(self.default_value, *self.value_range)
                )
        return self

    @property
    def default_validation_config(self) -> dict[str, bool]:
        return {"value_range": True, "strict": False}

    def validate_value(self, value: float, config: dict[str, bool] = None):
        _config = self.default_validation_config if config is None else config
        # mandatory validation
        self._validate_value_type(value)
        # optional validation
        if _config["value_range"]:
            self._validate_value_is_within_range(value, config=_config)

    @staticmethod
    def _validate_value_type(value: float):
        if not isinstance(value, float):
            if isinstance(value, int):
                # integers will be cast to floats
                print(
                    f"Warning: Value is of type int, but expected float."
                    f" It will be cast to float."
                    )
            else:
                raise TypeError(
                    f"Expected value to be of type {float} or {np.float64}, "
                    f"but received {type(value)}."
                )

    def _validate_value_is_within_range(self, value: float, config: dict[str, bool] = None):
        if not self._value_is_within_range(value):
            error_message = "Value ({}) of '{}' is out of valid range.".format(value, self.name)
            if self.value_range is not None:
                error_message = error_message[:-1] + " ([{},{}]).".format(*self.value_range)
            if config["strict"]:
                raise ValueError(error_message)
            else:
                print("Warning: " + error_message)

    def _value_is_within_range(self, value) -> bool:
        tolerances = {"rtol": 0, "atol": self.value_range_tolerance}

        is_within_range, is_within_tolerance = False, False
        if self.value_range is None:
            if self.default_value is None:
                # constant variables
                is_within_tolerance = True
            elif str(self.default_value) == "nan":
                # outputs
                is_within_tolerance = True
            else:
                # input variables with no specified range
                is_within_tolerance = np.isclose(value, self.default_value, **tolerances)
        # non-constant variables
        else:
            is_within_range = self.value_range[0] <= value <= self.value_range[1]
            is_within_tolerance = any([np.isclose(value, ele, **tolerances) for ele in self.value_range])
        return is_within_range or is_within_tolerance


def get_variable(name: str) -> Type[Variable]:
    """Returns the Variable subclass with the given name.

    Args:
        name: Name of the Variable subclass.

    Returns:
        Variable subclass with the given name.
    """
    classes = [ScalarVariable]
    class_lookup = {c.__name__: c for c in classes}
    if name not in class_lookup.keys():
        raise KeyError(f"No variable named {name}, valid names are {list(class_lookup.keys())}")
    return class_lookup[name]


# class NumpyNDArray(np.ndarray):
#     """
#     Custom type validator for numpy ndarray.
#     """
#
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, v: Any) -> np.ndarray:
#         # validate data...
#
#         if isinstance(v, list):
#             # conver to array, keep order
#             v = np.ndarray(v, order="K")
#
#         if not isinstance(v, np.ndarray):
#             logger.exception("A numpy array is required for the value")
#             raise TypeError("Numpy array required")
#         return v
#
#     class Config:
#         json_encoders = {
#             np.ndarray: lambda v: v.tolist(),  # may lose some precision
#         }


# class Image(np.ndarray):
#     """
#     Custom type validator for image array.
#
#     """
#
#     @classmethod
#     def __get_validators__(cls):
#         yield cls.validate
#
#     @classmethod
#     def validate(cls, v: Any) -> np.ndarray:
#         # validate data...
#         if not isinstance(v, np.ndarray):
#             logger.exception("Image variable value must be a numpy array")
#             raise TypeError("Numpy array required")
#
#         if (not v.ndim == 2 and not v.ndim == 3) or (v.ndim == 3 and v.shape[2] != 3):
#             logger.exception("Array must have dim=2 or dim=3 to instantiate image")
#             raise ValueError(
#                 f"Image array must have dim=2 or dim=3. Provided array has {v.ndim} dimensions"
#             )
#
#         return v


# class NDVariableBase:
#     """
#     Holds properties associated with numpy array variables.
#
#     Attributes:
#         shape (tuple): Shape of the numpy n-dimensional array
#     """
#
#     @property
#     def shape(self) -> tuple:
#         if self.default is not None:
#             return self.default.shape
#         else:
#             return None


# class ImageVariable(BaseModel, NDVariableBase):
#     """
#     Base class used for constructing an image variable.
#
#     Attributes:
#         variable_type (str): Indicates image variable.
#
#         axis_labels (List[str]): Labels to use for rendering axes.
#
#         axis_units (Optional[List[str]]): Units to use for rendering axes labels.
#
#         x_min_variable (Optional[str]): Scalar variable associated with image minimum x.
#
#         x_max_variable (Optional[str]): Scalar variable associated with image maximum x.
#
#         y_min_variable (Optional[str]): Scalar variable associated with image minimum y.
#
#         y_max_variable (Optional[str]): Scalar variable associated with image maximum y.
#     """
#
#     variable_type: str = "image"
#     axis_labels: List[str]
#     axis_units: Optional[List[str]]
#     x_min_variable: Optional[str]
#     x_max_variable: Optional[str]
#     y_min_variable: Optional[str]
#     y_max_variable: Optional[str]


# class ArrayVariable(BaseModel, NDVariableBase):
#     """
#     Base class used for constructing an array variable.  Array variables can capture
#     strings by passing `variable_type="string"` during initialization. Otherwise, the
#     value will default to an array of floats.
#
#     Attributes:
#         variable_type (str): Indicates array variable.
#
#         dim_labels (Optional[List[str]]): Labels to use for rendering axes.
#
#         units (Optional[List[str]]): Units to use for rendering axes labels.
#
#         value_type (Literal["float", "string"]): Type of value held by array.
#
#     """
#
#     variable_type: str = "array"
#     units: Optional[List[str]]  # required for some output displays
#     dim_labels: Optional[List[str]]
#     value_type: Literal["float", "string"] = "float"


# class ImageInputVariable(InputVariable[Image], ImageVariable):
#     """
#     Variable used for representing an image input. Image variable values must be two or
#     three dimensional arrays (grayscale, color, respectively). Initialization requires
#     name, axis_labels, default, x_min, x_max, y_min, y_max.
#
#     Attributes:
#
#         name (str): Name of the variable.
#         default (Value):  Default value assigned to the variable.
#         precision (Optional[int]): Precision to use for the value.
#         value (Optional[Value]): Value assigned to variable
#         value_range (list): Acceptable range for value
#         variable_type (str): Indicates image variable.
#         axis_labels (List[str]): Labels to use for rendering axes.
#         axis_units (Optional[List[str]]): Units to use for rendering axes labels.
#         x_min (float): Minimum x value of image.
#         x_max (float): Maximum x value of image.
#         y_min (float): Minimum y value of image.
#         y_max (float): Maximum y value of image.
#         x_min_variable (Optional[str]): Scalar variable associated with image minimum x.
#         x_max_variable (Optional[str]): Scalar variable associated with image maximum x.
#         y_min_variable (Optional[str]): Scalar variable associated with image minimum y.
#         y_max_variable (Optional[str]): Scalar variable associated with image maximum y.
#
#
#     Example:
#         ```
#         variable = ImageInputVariable(
#             name="test",
#             default=np.array([[1,4], [5,2]]),
#             value_range=[1, 10],
#             axis_labels=["count_1", "count_2"],
#             x_min=0,
#             y_min=0,
#             x_max=5,
#             y_max=5,
#         )
#         ```
#
#     """
#
#     x_min: float
#     x_max: float
#     y_min: float
#     y_max: float


# class ImageOutputVariable(OutputVariable[Image], ImageVariable):
#     """
#     Variable used for representing an image output. Image variable values must be two or
#     three dimensional arrays (grayscale, color, respectively). Initialization requires
#     name and axis_labels.
#
#     Attributes:
#         name (str): Name of the variable.
#         default (Optional[Value]):  Default value assigned to the variable.
#         precision (Optional[int]): Precision to use for the value.
#         value (Optional[Value]): Value assigned to variable
#         value_range (Optional[list]): Acceptable range for value
#         variable_type (str): Indicates image variable.
#         axis_labels (List[str]): Labels to use for rendering axes.
#         axis_units (Optional[List[str]]): Units to use for rendering axes labels.
#         x_min (Optional[float]): Minimum x value of image.
#         x_max (Optional[float]): Maximum x value of image.
#         y_min (Optional[float]): Minimum y value of image.
#         y_max (Optional[float]): Maximum y value of image.
#         x_min_variable (Optional[str]): Scalar variable associated with image minimum x.
#         x_max_variable (Optional[str]): Scalar variable associated with image maximum x.
#         y_min_variable (Optional[str]): Scalar variable associated with image minimum y.
#         y_max_variable (Optional[str]): Scalar variable associated with image maximum y.
#
#     Example:
#         ```
#         variable =  ImageOutputVariable(
#             name="test",
#             default=np.array([[2 , 1], [1, 4]]),
#             axis_labels=["count_1", "count_2"],
#         )
#
#         ```
#
#
#     """
#
#     x_min: Optional[float] = None
#     x_max: Optional[float] = None
#     y_min: Optional[float] = None
#     y_max: Optional[float] = None


# class ArrayInputVariable(InputVariable[NumpyNDArray], ArrayVariable):
#     """
#     Variable used for representing an array input. Array variables can capture
#     strings by passing `variable_type="string"` during initialization. Otherwise, the
#     value will default to an array of floats.
#
#     Attributes:
#         name (str): Name of the variable.
#         default (np.ndarray):  Default value assigned to the variable.
#         precision (Optional[int]): Precision to use for the value.
#         value (Optional[Value]): Value assigned to variable
#         value_range (Optional[list]): Acceptable range for value
#         variable_type (str): Indicates array variable.
#         dim_labels (List[str]): Labels to use for dimensions
#         dim_units (Optional[List[str]]): Units to use for dimensions.
#
#     """
#
#     pass


# class ArrayOutputVariable(OutputVariable[NumpyNDArray], ArrayVariable):
#     """
#     Variable used for representing an array output. Array variables can capture
#     strings by passing `variable_type="string"` during initialization. Otherwise, the
#     value will default to an array of floats.
#
#     Attributes:
#         name (str): Name of the variable.
#
#         default (Optional[np.ndarray]):  Default value assigned to the variable.
#
#         precision (Optional[int]): Precision to use for the value.
#
#         value (Optional[Value]): Value assigned to variable
#
#         value_range (Optional[list]): Acceptable range for value
#
#         variable_type (str): Indicates array variable.
#
#         dim_labels (List[str]): Labels to use for dimensions
#
#         dim_units (Optional[List[str]]): Units to use for dimensions.
#     """
#
#     pass


# class TableVariable(BaseModel):
#     """Table variables are used for creating tabular representations of data. Table variables should only be used for client tools.
#
#     Attributes:
#         table_rows (Optional[List[str]]): List of rows to assign to array data.
#         table_data (dict): Dictionary representation of columns and rows.
#         rows (list): List of rows.
#         columns (list): List of columns.
#     """
#
#     table_rows: Optional[List[str]] = None
#     table_data: dict
#
#     @property
#     def columns(self) -> tuple:
#         if self.table_data is not None:
#             return list(self.table_data.keys())
#         else:
#             return None
#
#     @validator("table_rows")
#     def validate_rows(cls, v):
#         if isinstance(v, list):
#             for val in v:
#                 if not isinstance(val, str):
#                     raise TypeError("Rows must be defined as strings")
#
#         else:
#             raise TypeError("Rows must be passed as list")
#
#         return v
#
#     @validator("table_data")
#     def table_data_formatted(cls, v, values) -> dict:
#         passed_rows = values.get("table_rows", None)
#         # validate data...
#         if not isinstance(v, dict):
#             logger.exception(
#                 "Must provide dictionary representation of table structure, outer level columns, inner level rows."
#             )
#             raise TypeError("Dictionary required")
#
#         # check that rows are represented in structure
#         for val in v.values():
#             if not isinstance(val, (dict, ArrayVariable)):
#                 logger.exception(
#                     "Rows are not represented in structure. Structure should map column title to either dictionary of row names and values or array variables."
#                 )
#                 raise TypeError(
#                     "Rows are not represented in structure. Structure should map column title to either dictionary of row names and values or array variables."
#                 )
#
#             if isinstance(val, ArrayVariable):
#                 if passed_rows is None:
#                     logger.exception("Must pass table_rows when using array variables.")
#                     raise TypeError("Must pass table_rows when using array variables.")
#
#                 # shape must match length of passed rows
#                 elif val.shape[0] != len(passed_rows):
#                     raise TypeError(
#                         "Array first dimension must match passed rows length."
#                     )
#
#         # check row structures to make sure properly formatted
#         for val in v.values():
#
#             # check row dictionary
#             if isinstance(val, dict):
#                 if val.get("variable_type", None) is None:
#                     for row_val in val.values():
#                         if not isinstance(row_val, (dict, ScalarVariable, float)):
#                             logger.exception(
#                                 "Row dictionary must map row names to ScalarVariables or float."
#                             )
#                             raise TypeError(
#                                 "Row dictionary must map row names to ScalarVariables or float."
#                             )
#
#                         # check that row keys align
#                         if isinstance(row_val, dict) and passed_rows is not None:
#                             row_rep = row_val.keys()
#                             for row in row_rep:
#                                 if row not in passed_rows:
#                                     raise TypeError(
#                                         f"Row {row} not in row list passed during construction."
#                                     )
#         return v
#
#     @property
#     def rows(self) -> tuple:
#         if self.table_rows is not None:
#             return self.table_rows
#         else:
#             struct_rows = []
#             for col, row_item in self.table_data.items():
#                 if isinstance(row_item, dict):
#                     struct_rows += list(row_item.keys())
#             return list(set(struct_rows))
