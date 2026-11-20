// Copyright (c) 2020 Ultimaker B.V.
// CuraEngine is released under the terms of the AGPLv3 or higher.

#ifndef GEOMETRY_POINT_MATRIX_H
#define GEOMETRY_POINT_MATRIX_H

#include <array>
#include <cmath>
#if defined(__SSE2__) && defined(__x86_64__)
#include <emmintrin.h>
#endif

#include "geometry/Point2LL.h"


namespace cura
{

class AngleDegrees;
class AngleRadians;

class PointMatrix
{
public:
    std::array<double, 4> matrix{ 1, 0, 0, 1 };

    PointMatrix() noexcept = default;

    explicit PointMatrix(double rotation);

    explicit PointMatrix(const AngleDegrees& rotation);

    explicit PointMatrix(const AngleRadians& rotation);

    explicit PointMatrix(const Point2LL& p);

    static PointMatrix scale(double s);

    /*!
     * Round to the nearest integer (ties to even), exactly like std::llrint() in the default rounding mode, but inlined as a single
     * cvtsd2si instruction instead of a libm call. These conversions run once per coordinate and dominate polygon rotation.
     */
    [[nodiscard]] static inline long long roundToCoord(const double v) noexcept
    {
#if defined(__SSE2__) && defined(__x86_64__)
        return _mm_cvtsd_si64(_mm_set_sd(v));
#else
        return std::llrint(v);
#endif
    }

    [[nodiscard]] inline Point2LL apply(const Point2LL& p) const
    {
        const auto x = static_cast<double>(p.X);
        const auto y = static_cast<double>(p.Y);
        return { roundToCoord(x * matrix[0] + y * matrix[1]), roundToCoord(x * matrix[2] + y * matrix[3]) };
    }

    /*!
     * \warning only works on a rotation matrix! Output is incorrect for other types of matrix
     */
    [[nodiscard]] inline Point2LL unapply(const Point2LL& p) const
    {
        const auto x = static_cast<double>(p.X);
        const auto y = static_cast<double>(p.Y);
        return { roundToCoord(x * matrix[0] + y * matrix[2]), roundToCoord(x * matrix[1] + y * matrix[3]) };
    }

    [[nodiscard]] PointMatrix inverse() const;
};

} // namespace cura
#endif // GEOMETRY_POINT_MATRIX_H
