# -*- encoding: utf-8 -*-
"""
Copyright (C) 2024, The YunmengEnvs Contributors. Join us, for you talents!  

Fields definition.
"""
from abc import abstractmethod
from typing import Callable, Union, List
import numpy as np

from core.numerics.fields.variables import Variable, Scalar, Vector, Tensor


class Field:
    """
    Abstract field class.
    """

    def __init__(self, num_vars: int, default: Variable):
        """
        Initialize the field with a given number of variables and a default value.

        Args:
            num_vars: The number of variables in the field.
            default: The default value of each variable.
        """
        self._num_vars = num_vars
        self._default = default
        self._values = np.full(num_vars, default)

    # -----------------------------------------------
    # --- Properties and auxiliary methods ---
    # -----------------------------------------------

    @property
    def type(self) -> str:
        """
        Get the type of the field, e.g. "scalar", "vector", "tensor".
        """
        return self._default.type

    @property
    @abstractmethod
    def domain(self) -> str:
        """
        Get the domain of the field, e.g. "cell", "face", "node".
        """
        raise NotImplementedError

    def filter(self, func: Callable) -> List[int]:
        """
        Filter the field by a given function.

        Args:
            func: Function taking a variable as input and returning a boolean value.

        Returns:
            The filtered variable indices.
        """
        # vectorize the function to apply it to each variable
        vectorized_func = np.vectorize(func)
        mask = vectorized_func(self._values)

        # get the variables that satisfy the condition
        indices = np.where(mask)[0]
        return indices.tolist()

    def for_each(self, func: Callable):
        """
        Apply a function to each variable of the field.

        Args:
            func: Function taking a variable as input.
        """
        if not callable(func):
            raise TypeError(f"Invalid function type: {type(func)}")

        for i in range(self._num_vars):
            res = func(self._values[i])
            if isinstance(res, Variable) and res.type == self.type:
                self._values[i] = res

    def at(self, indexes: List[int], func: Callable):
        """
        Apply a function to a variable of the field at given position.

        Args:
            indexes: The index of the variable to apply the function to.
            func: Function taking a variable as input.
        """
        if not callable(func):
            raise TypeError(f"Invalid function type: {type(func)}")

        min_index = min(indexes)
        max_index = max(indexes)
        if min_index < 0 or max_index >= self._num_vars:
            raise IndexError(f"Index out of range: {min_index}/{max_index}")

        for i in indexes:
            res = func(self._values[i])
            if isinstance(res, Variable) and res.type == self.type:
                self._values[i] = res

    def assign(self, other: Union["Field", "Variable"]):
        """
        Assign the values of another field or a variable to the current field.

        Args:
            other: The other field or variable to assign.
        """
        if isinstance(other, Field):
            try:
                self._check_fields_compatible(other)
            except (ValueError, TypeError) as e:
                raise TypeError(f"Cannot assign fields: {e}")

            self._values = other._values
        elif isinstance(other, Variable):
            if other.type != self.type:
                raise TypeError(
                    f"Invalid value type: {other.type} (expected {self.type})"
                )

            self._values = np.full(self._num_vars, other)
        else:
            raise TypeError(f"Cannot assign {type(other)} to field")

    # -----------------------------------------------
    # --- reload query methods ---
    # -----------------------------------------------

    def __getitem__(self, index: int) -> Variable:
        """
        Get the value of the field at a given position.
        """
        return self._values[index]

    def __setitem__(self, index: int, value: Variable):
        """
        Set the value of the field at a given position.
        """
        if value.type != self._default.type:
            raise TypeError(
                f"Invalid value type: {value.type} (expected {self._default.type})"
            )

        self._values[index] = value

    def __len__(self) -> int:
        """
        Get the number of variables in the field.
        """
        return self._num_vars

    def __iter__(self):
        """
        Iterate over the variables in the field.
        """
        for i in range(self._num_vars):
            yield self._values[i]

    # -----------------------------------------------
    # --- reload arithmetic operations ---
    # -----------------------------------------------

    def _check_fields_compatible(self, other: "Field"):
        """
        Check if two fields are compatible for arithmetic operations.
        """
        if self._num_vars != other._num_vars:
            raise ValueError("Fields must have the same number of variables")

        if self.type != other.type:
            raise TypeError("Fields must have the same default value type")

        if self.domain != other.domain:
            raise TypeError("Fields must have the same domain")

    def __add__(self, other: Union["Field", "Variable"]) -> "Field":
        """
        Add two fields or a field and a constant element-wise.
        """
        if isinstance(other, Field):
            try:
                self._check_fields_compatible(other)
            except (ValueError, TypeError) as e:
                raise TypeError(f"Cannot add fields: {e}")

            result = self.__class__(self._num_vars, self._default)
            result._values = self._values + other._values
            return result
        elif isinstance(other, Variable):
            if other.type != self._default.type:
                raise TypeError(
                    f"Invalid value type: {other.type} (expected {self._default.type})"
                )

            def add_constant(x):
                return x + other

            result = self.__class__(self._num_vars, self._default)
            result._values = np.vectorize(add_constant)(self._values)
            return result
        else:
            raise TypeError(f"Cannot add {type(other)} to field")

    def __sub__(self, other: Union["Field", "Variable"]) -> "Field":
        """
        Subtract two fields or a field and a constant element-wise.
        """
        if isinstance(other, Field):
            try:
                self._check_fields_compatible(other)
            except (ValueError, TypeError) as e:
                raise TypeError(f"Cannot subtract fields: {e}")

            result = self.__class__(self._num_vars, self._default)
            result._values = self._values - other._values
            return result
        elif isinstance(other, Variable):
            if other.type != self._default.type:
                raise TypeError(
                    f"Invalid value type: {other.type} (expected {self._default.type})"
                )

            def sub_constant(x):
                return x - other

            result = self.__class__(self._num_vars, self._default)
            result._values = np.vectorize(sub_constant)(self._values)
            return result
        else:
            raise TypeError(f"Cannot subtract {type(other)} from field")

    def __mul__(self, other: Scalar) -> "Field":
        """
        Multiply the field by a scalar element-wise.
        """
        if not isinstance(other, Scalar):
            raise TypeError(f"Cannot multiply field by {type(other)}")

        result = self.__class__(self._num_vars, self._default)
        result._values = self._values * other
        return result

    def __truediv__(self, other: Scalar) -> "Field":
        """
        Divide the field by a scalar element-wise.
        """
        if not isinstance(other, Scalar):
            raise TypeError(f"Cannot divide field by {type(other)}")

        result = self.__class__(self._num_vars, self._default)
        result._values = self._values / other
        return result

    def __neg__(self) -> "Field":
        """
        Negate the field element-wise.
        """
        result = self.__class__(self._num_vars, self._default)
        result._values = -self._values
        return result

    def __abs__(self) -> "Field":
        """
        Take the absolute value of the field element-wise.
        """
        result = self.__class__(self._num_vars, self._default)
        result._values = np.abs(self._values)
        return result


class CellField(Field):
    """
    Cell field which represents statues of cells.

    Default at each cell center.
    """

    def __init__(self, num_cells: int, default: Variable):
        """
        Initialize the cell field with a given number of cells and a default value.

        Args:
            num_cells: The number of cells in the field.
            default: The default value of each cell.
        """
        super().__init__(num_cells, default)

    @property
    def domain(self) -> str:
        """
        Get the domain of the field, which is "cell".
        """
        return "cell"


class FaceField(Field):
    """
    Face field which represents statues of faces.

    Default at each face center.
    """

    def __init__(self, num_faces: int, default: Variable):
        """
        Initialize the face field with a given number of faces and a default value.

        Args:
            num_faces: The number of faces in the field.
            default: The default value of each face.
        """
        super().__init__(num_faces, default)

    @property
    def domain(self) -> str:
        """
        Get the domain of the field, which is "face".
        """
        return "face"


class NodeField(Field):
    """
    Node field which represents statues of nodes.
    """

    def __init__(self, num_nodes: int, default: Variable):
        """
        Initialize the node field with a given number of nodes and a default value.

        Args:
            num_nodes: The number of nodes in the field.
            default: The default value of each node.
        """
        super().__init__(num_nodes, default)

    @property
    def domain(self) -> str:
        """
        Get the domain of the field, which is "node".
        """
        return "node"
