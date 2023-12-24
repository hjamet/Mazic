"""This file contains the is_in_triangle function, which is an efficient way of finding out whether a point is in a triangle or not."""

import numpy as np
import pandas as pd


def ft_is_in_triangle(
    points: pd.DataFrame,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
):
    """Return a boolean array indicating whether each point is in the triangle or not.

    Args:
        points (pd.DataFrame): A DataFrame containing the points to check.
        x1 (float): The x coordinate of the first point of the triangle.
        y1 (float): The y coordinate of the first point of the triangle.
        x2 (float): The x coordinate of the second point of the triangle.
        y2 (float): The y coordinate of the second point of the triangle.
        x3 (float): The x coordinate of the third point of the triangle.
        y3 (float): The y coordinate of the third point of the triangle.

    Returns:
        np.array: An index array of all the points inside the triangle.
    """
    # Convert points to numpy array
    points = points.to_numpy()

    # Prepare triangle points for broadcasting
    tri_p1 = np.array([x1, y1])
    tri_p2 = np.array([x2, y2])
    tri_p3 = np.array([x3, y3])

    # Calculate areas signs for points with respect to triangle sides
    sign_p1p2 = __sign(points, tri_p1, tri_p2)
    sign_p2p3 = __sign(points, tri_p2, tri_p3)
    sign_p3p1 = __sign(points, tri_p3, tri_p1)

    # Check if points are in triangle
    inside = __check_same_sign(sign_p1p2, sign_p2p3, sign_p3p1)

    return np.where(inside)[0]


# Fonctions pour calculer les aires signées des triangles
def __sign(p1: np.array, p2: np.array, p3: np.array):
    return (p1[:, 0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[:, 1] - p3[1])


# Vérifier si chaque point est à gauche de chaque côté du triangle
def __check_same_sign(a: np.array, b: np.array, c: np.array):
    return np.logical_and(np.logical_and(a < 0, b < 0), c < 0) | np.logical_and(
        np.logical_and(a > 0, b > 0), c > 0
    )


# ---------------------------------- EXAMPLE --------------------------------- #

if __name__ == "__main__":
    # Coordonnées du triangle
    x1, y1 = 0.1, 0.2
    x2, y2 = 0.4, 0.8
    x3, y3 = 0.7, 0.3

    # Créons un DataFrame de test
    points = pd.DataFrame({"x": np.random.rand(100), "y": np.random.rand(100)})

    inside = ft_is_in_triangle(points, x1, y1, x2, y2, x3, y3)

    print(inside)
