// Copyright (c) 2025 UltiMaker
// CuraEngine is released under the terms of the AGPLv3 or higher.

#include "geometry/PointMatrix.h"

#include <numbers>

#include "settings/types/Angle.h"


namespace cura
{

PointMatrix::PointMatrix(double rotation)
{
    rotation = rotation / 180 * std::numbers::pi;
    matrix.at(0) = std::cos(rotation);
    matrix.at(1) = -std::sin(rotation);
    matrix.at(2) = -matrix.at(1);
    matrix.at(3) = matrix.at(0);
}

PointMatrix::PointMatrix(const AngleDegrees& rotation)
    : PointMatrix(rotation.value_)
{
}

PointMatrix::PointMatrix(const AngleRadians& rotation)
    : PointMatrix(AngleDegrees(rotation))
{
}

PointMatrix::PointMatrix(const Point2LL& p)
{
    matrix.at(0) = static_cast<double>(p.X);
    matrix.at(1) = static_cast<double>(p.Y);
    double f = std::sqrt((matrix.at(0) * matrix.at(0)) + (matrix.at(1) * matrix.at(1)));
    matrix.at(0) /= f;
    matrix.at(1) /= f;
    matrix.at(2) = -matrix.at(1);
    matrix.at(3) = matrix.at(0);
}

PointMatrix PointMatrix::scale(double s)
{
    PointMatrix ret;
    ret.matrix.at(0) = s;
    ret.matrix.at(3) = s;
    return ret;
}

PointMatrix PointMatrix::inverse() const
{
    PointMatrix ret;
    double det = matrix.at(0) * matrix.at(3) - matrix.at(1) * matrix.at(2);
    ret.matrix.at(0) = matrix.at(3) / det;
    ret.matrix.at(1) = -matrix.at(1) / det;
    ret.matrix.at(2) = -matrix.at(2) / det;
    ret.matrix.at(3) = matrix.at(0) / det;
    return ret;
}

} // namespace cura
