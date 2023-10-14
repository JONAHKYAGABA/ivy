# local

import ivy
from ivy.func_wrapper import with_unsupported_dtypes, with_supported_dtypes
from ivy.functional.frontends.paddle.func_wrapper import (
    to_ivy_arrays_and_back,
)
from ivy.functional.frontends.torch.nn.functional import cubic_conv2, cubic_conv1
from ivy.utils.assertions import check_equal
from ivy.utils.exceptions import IvyNotImplementedException


@to_ivy_arrays_and_back
@with_unsupported_dtypes({"2.5.1 and below": ("float16", "bfloat16")}, "paddle")
def affine_grid(theta, out_shape, align_corners=True):
    if len(out_shape) == 4:
        N, C, H, W = out_shape
        base_grid = ivy.empty((N, H, W, 3))
        if align_corners:
            base_grid[:, :, :, 0] = ivy.linspace(-1, 1, W)
            base_grid[:, :, :, 1] = ivy.expand_dims(ivy.linspace(-1, 1, H), axis=-1)
            height_values = ivy.expand_dims(ivy.linspace(-1, 1, H), axis=-1)
            base_grid[:, :, :, 1] = ivy.array(
                [[[height_values[i]] * W for i in range(H)]]
            )[:, :, :, 0]
            base_grid[:, :, :, 2] = ivy.full((H, W), 1)
            grid = ivy.matmul(base_grid.view((N, H * W, 3)), theta.swapaxes(1, 2))
            return grid.view((N, H, W, 2))
        else:
            base_grid[:, :, :, 0] = ivy.linspace(-1, 1, W) * (W - 1) / W
            base_grid[:, :, :, 1] = ivy.expand_dims(
                ivy.linspace(-1, 1, H) * (H - 1) / H, axis=-1
            )
            height_values = ivy.expand_dims(
                ivy.linspace(-1, 1, H) * (H - 1) / H, axis=-1
            )
            base_grid[:, :, :, 1] = ivy.array(
                [[[height_values[i]] * W for i in range(H)]]
            )[:, :, :, 0]
            base_grid[:, :, :, 2] = ivy.full((H, W), 1)
        grid = ivy.matmul(base_grid.view((N, H * W, 3)), ivy.swapaxes(theta, 1, 2))
        return grid.view((N, H, W, 2))
    else:
        N, C, D, H, W = out_shape
        base_grid = ivy.empty((N, D, H, W, 4))
        if align_corners:
            base_grid[:, :, :, :, 0] = ivy.linspace(-1, 1, W)
            base_grid[:, :, :, :, 1] = ivy.expand_dims(ivy.linspace(-1, 1, H), axis=-1)
            height_values = ivy.linspace(-1, 1, H)
            base_grid[:, :, :, :, 1] = ivy.array(
                [[[[height_values[i]] * W for i in range(H)]] * D]
            )
            base_grid[:, :, :, :, 2] = ivy.expand_dims(
                ivy.expand_dims(ivy.linspace(-1, 1, D), axis=-1), axis=-1
            )
            width_values = ivy.linspace(-1, 1, D)
        else:
            base_grid[:, :, :, :, 0] = ivy.linspace(-1, 1, W) * (W - 1) / W
            base_grid[:, :, :, :, 1] = ivy.expand_dims(
                ivy.linspace(-1, 1, H) * (H - 1) / H, axis=-1
            )
            height_values = ivy.linspace(-1, 1, H) * (H - 1) / H
            base_grid[:, :, :, :, 1] = ivy.array(
                [[[[height_values[i]] * W for i in range(H)]] * D]
            )
            base_grid[:, :, :, :, 2] = ivy.expand_dims(
                ivy.expand_dims(ivy.linspace(-1, 1, D) * (D - 1) / D, axis=-1), axis=-1
            )
            width_values = ivy.linspace(-1, 1, D) * (D - 1) / D

        base_grid[:, :, :, :, 2] = ivy.array(
            [[ivy.array([[width_values[i]] * W] * H) for i in range(D)]]
        )
        base_grid[:, :, :, :, 3] = ivy.full((D, H, W), 1)
        grid = ivy.matmul(base_grid.view((N, D * H * W, 4)), theta.swapaxes(1, 2))
        return grid.view((N, D, H, W, 3))


@to_ivy_arrays_and_back
@with_supported_dtypes({"2.5.1 and below": ("float32", "float64")}, "paddle")
def channel_shuffle(x, groups, data_format="NCHW", name=None):
    if len(ivy.shape(x)) != 4:
        raise ValueError(
            "Input x should be 4D tensor, but received x with the shape of"
            f" {ivy.shape(x)}"
        )

    if not isinstance(groups, int):
        raise TypeError("groups must be int type")

    if groups <= 0:
        raise ValueError("groups must be positive")

    if data_format not in ["NCHW", "NHWC"]:
        raise ValueError(
            "Attr(data_format) should be 'NCHW' or 'NHWC'.But receive"
            f" Attr(data_format): {data_format} "
        )

    if data_format == "NCHW":
        b, c, h, w = ivy.shape(x)
        x = ivy.reshape(x, (b, groups, c // groups, h, w))
        x = ivy.permute_dims(x, (0, 2, 1, 3, 4))
        x = ivy.reshape(x, (b, c, h, w))
    else:
        b, h, w, c = ivy.shape(x)
        x = ivy.reshape(x, (b, h, w, groups, c // groups))
        x = ivy.permute_dims(x, (0, 1, 2, 4, 3))
        x = ivy.reshape(x, (b, h, w, c))
    return x


@to_ivy_arrays_and_back
def pixel_shuffle(x, upscale_factor, data_format="NCHW"):
    input_shape = ivy.shape(x)
    check_equal(
        len(input_shape),
        4,
        message=f"pixel shuffle requires a 4D input, but got input size {input_shape}",
    )

    if not isinstance(upscale_factor, int):
        raise ValueError("upscale factor must be int type")

    if data_format not in ["NCHW", "NHWC"]:
        raise ValueError(
            "Attr(data_format) should be 'NCHW' or 'NHWC'.But receive"
            f" Attr(data_format): {data_format} "
        )

    b = input_shape[0]
    c = input_shape[1] if data_format == "NCHW" else input_shape[3]
    h = input_shape[2] if data_format == "NCHW" else input_shape[1]
    w = input_shape[3] if data_format == "NCHW" else input_shape[2]

    upscale_factor_squared = upscale_factor**2

    check_equal(
        c % upscale_factor_squared,
        0,
        message=(
            "pixel shuffle expects input channel to be divisible by square of upscale"
            f" factor, but got input with sizes {input_shape}, upscale"
            f" factor={upscale_factor}, and self.size(1)={c}, is not divisible by"
            f" {upscale_factor_squared}"
        ),
        as_array=False,
    )

    oc = int(c / upscale_factor_squared)
    oh = h * upscale_factor
    ow = w * upscale_factor

    if data_format == "NCHW":
        input_reshaped = ivy.reshape(x, (b, oc, upscale_factor, upscale_factor, h, w))
    else:
        input_reshaped = ivy.reshape(x, (b, h, w, upscale_factor, upscale_factor, oc))

    if data_format == "NCHW":
        return ivy.reshape(
            ivy.permute_dims(input_reshaped, (0, 1, 4, 2, 5, 3)), (b, oc, oh, ow)
        )
    return ivy.reshape(
        ivy.permute_dims(input_reshaped, (0, 1, 4, 2, 5, 3)), (b, oh, ow, oc)
    )


@to_ivy_arrays_and_back
def pixel_unshuffle(x, downscale_factor, data_format="NCHW"):
    if len(ivy.shape(x)) != 4:
        raise ValueError(
            "Input x should be 4D tensor, but received x with the shape of"
            f" {ivy.shape(x)}"
        )

    if not isinstance(downscale_factor, int):
        raise ValueError("Downscale factor must be int type")

    if downscale_factor <= 0:
        raise ValueError("Downscale factor must be positive")

    if data_format not in ["NCHW", "NHWC"]:
        raise ValueError(
            "Attr(data_format) should be 'NCHW' or 'NHWC'.But receive"
            f" Attr(data_format): {data_format} "
        )

    if data_format == "NCHW":
        b, c, h, w = ivy.shape(x)
        oc = c * downscale_factor**2
        oh = h // downscale_factor
        ow = w // downscale_factor

        x = ivy.reshape(x, (b, c, oh, downscale_factor, ow, downscale_factor))
        x = ivy.permute_dims(x, (0, 1, 3, 5, 2, 4))
        x = ivy.reshape(x, (b, oc, oh, ow))
    else:
        b, h, w, c = ivy.shape(x)
        oc = c * downscale_factor**2
        oh = h // downscale_factor
        ow = w // downscale_factor

        x = ivy.reshape(x, (b, downscale_factor, oh, downscale_factor, ow, c))
        x = ivy.permute_dims(x, (0, 1, 3, 5, 2, 4))
        x = ivy.reshape(x, (b, oh, ow, oc))
    return x





@to_ivy_arrays_and_back
def grid_sample(
    input, grid, mode="bilinear", padding_mode="zeros", align_corners=False
):
    input_clone = ivy.copy_array(input)
    grid_clone = ivy.copy_array(grid)

    if ivy.get_num_dims(input_clone) == 4:  # sample from 2D images
        n, c, h, w = input_clone.shape
        n, to_h, to_w, gc = grid_clone.shape

        # Un-normalize 2D grid
        if align_corners:  # to range[0, size - 1]
            grid_clone[..., 0] = ((grid_clone[..., 0] + 1) / 2) * (w - 1)
            grid_clone[..., 1] = ((grid_clone[..., 1] + 1) / 2) * (h - 1)

        elif not align_corners:  # to range[0.5, size - 0.5]
            grid_clone[..., 0] = ((grid_clone[..., 0] + 1) * w - 1) / 2
            grid_clone[..., 1] = ((grid_clone[..., 1] + 1) * h - 1) / 2

        batch_coor = ivy.reshape(ivy.arange(n), (-1, 1))
        batch_coor = ivy.repeat(batch_coor, to_h * to_w, axis=1)
        batch_coor = ivy.reshape(batch_coor, (n, to_h, to_w))
        padding = [(0, 0) for _ in range(2)] + [(4, 4) for _ in range(2)]
        input_clone = ivy.pad(input_clone, padding, mode="constant", constant_values=0)

        if mode == "bicubic":
            grid_floor = ivy.floor(grid_clone)
            distance = grid_clone - grid_floor

            tx, ty = distance[..., 0], distance[..., 1]

            grid_floor -= 1
            grid_floor = [
                grid_sample_padding(
                    grid_floor + i, padding_mode, align_corners, borders=[w, h]
                )
                for i in range(4)
            ]

            w_cubic = [
                ivy.astype(grid_floor[i][..., 0] + 4, ivy.int64) for i in range(4)
            ]
            h_cubic = [
                ivy.astype(grid_floor[i][..., 1] + 4, ivy.int64) for i in range(4)
            ]

            coeffs = [
                bicubic_interp(
                    [
                        ivy.permute_dims(
                            input_clone[batch_coor, :, h_cubic[i], w_cubic[0]],
                            (0, 3, 1, 2),
                        ),
                        ivy.permute_dims(
                            input_clone[batch_coor, :, h_cubic[i], w_cubic[1]],
                            (0, 3, 1, 2),
                        ),
                        ivy.permute_dims(
                            input_clone[batch_coor, :, h_cubic[i], w_cubic[2]],
                            (0, 3, 1, 2),
                        ),
                        ivy.permute_dims(
                            input_clone[batch_coor, :, h_cubic[i], w_cubic[3]],
                            (0, 3, 1, 2),
                        ),
                    ],
                    tx,
                )
                for i in range(4)
            ]
            return bicubic_interp(coeffs, ty)

        else:
            grid_clone = grid_sample_padding(
                grid_clone, padding_mode, align_corners, borders=[w, h]
            )

        if mode == "bilinear":
            grid_clone += 4
            w_coor = ivy.reshape(grid_clone[..., 0], (n, to_h, to_w))
            h_coor = ivy.reshape(grid_clone[..., 1], (n, to_h, to_w))

            w0 = ivy.astype(ivy.floor(w_coor), ivy.int64)
            h0 = ivy.astype(ivy.floor(h_coor), ivy.int64)
            w1 = w0 + 1
            h1 = h0 + 1

            v00 = ivy.permute_dims(input_clone[batch_coor, :, h0, w0], (0, 3, 1, 2))
            v01 = ivy.permute_dims(input_clone[batch_coor, :, h0, w1], (0, 3, 1, 2))
            v10 = ivy.permute_dims(input_clone[batch_coor, :, h1, w0], (0, 3, 1, 2))
            v11 = ivy.permute_dims(input_clone[batch_coor, :, h1, w1], (0, 3, 1, 2))

            alpha = ivy.reshape(w_coor - w0, (n, 1, to_h, to_w))
            beta = ivy.reshape(h_coor - h0, (n, 1, to_h, to_w))

            alpha = ivy.astype(alpha, ivy.float32)
            beta = ivy.astype(beta, ivy.float32)

            v0 = v00 * (1 - alpha) + v01 * alpha
            v1 = v10 * (1 - alpha) + v11 * alpha

            return v0 * (1 - beta) + v1 * beta

        elif mode == "nearest":
            w_coor = ivy.reshape(grid_clone[..., 0], (n, to_h, to_w))
            h_coor = ivy.reshape(grid_clone[..., 1], (n, to_h, to_w))

            w_coor = ivy.astype(ivy.round(w_coor), ivy.int64) + 4
            h_coor = ivy.astype(ivy.round(h_coor), ivy.int64) + 4
            return ivy.permute_dims(
                input_clone[batch_coor, :, h_coor, w_coor], (0, 3, 1, 2)
            )

        else:
            raise ivy.exceptions.IvyError(f"Not supported mode {mode}")

    elif ivy.get_num_dims(input_clone) == 5:  # sample from 3D images
        n, c, d, h, w = input_clone.shape
        n, to_d, to_h, to_w, gc = grid_clone.shape

        # Un-normalize 3D grid
        if align_corners:  # to range[0, size - 1]
            grid_clone[..., 0] = ((grid_clone[..., 0] + 1) / 2) * (w - 1)
            grid_clone[..., 1] = ((grid_clone[..., 1] + 1) / 2) * (h - 1)
            grid_clone[..., 2] = ((grid_clone[..., 2] + 1) / 2) * (d - 1)
        elif not align_corners:  # to range[0.5, size - 0.5]
            grid_clone[..., 0] = ((grid_clone[..., 0] + 1) * w - 1) / 2
            grid_clone[..., 1] = ((grid_clone[..., 1] + 1) * h - 1) / 2
            grid_clone[..., 2] = ((grid_clone[..., 2] + 1) * d - 1) / 2

        batch_coor = ivy.reshape(ivy.arange(n), (-1, 1))
        batch_coor = ivy.repeat(batch_coor, to_d * to_h * to_w, axis=1)
        batch_coor = ivy.reshape(batch_coor, (n, to_d, to_h, to_w))
        padding = [(0, 0) for _ in range(2)] + [(3, 3) for _ in range(3)]
        input_clone = ivy.pad(input_clone, padding, mode="constant", constant_values=0)

        grid_clone = grid_sample_padding(
            grid_clone, padding_mode, align_corners, borders=[w, h, d]
        )

        if mode == "bilinear":
            grid_clone += 3
            w_coor = ivy.reshape(grid_clone[..., 0], (n, to_d, to_h, to_w))
            h_coor = ivy.reshape(grid_clone[..., 1], (n, to_d, to_h, to_w))
            d_coor = ivy.reshape(grid_clone[..., 2], (n, to_d, to_h, to_w))

            w0 = ivy.astype(ivy.floor(w_coor), ivy.int64)
            h0 = ivy.astype(ivy.floor(h_coor), ivy.int64)
            d0 = ivy.astype(ivy.floor(d_coor), ivy.int64)
            w1 = w0 + 1
            h1 = h0 + 1
            d1 = d0 + 1

            v000 = ivy.permute_dims(
                input_clone[batch_coor, :, d0, h0, w0], (0, 4, 1, 2, 3)
            )  # tnw
            v001 = ivy.permute_dims(
                input_clone[batch_coor, :, d0, h0, w1], (0, 4, 1, 2, 3)
            )  # tne
            v010 = ivy.permute_dims(
                input_clone[batch_coor, :, d0, h1, w0], (0, 4, 1, 2, 3)
            )  # tsw
            v011 = ivy.permute_dims(
                input_clone[batch_coor, :, d0, h1, w1], (0, 4, 1, 2, 3)
            )  # tse
            v100 = ivy.permute_dims(
                input_clone[batch_coor, :, d1, h0, w0], (0, 4, 1, 2, 3)
            )  # bnw
            v101 = ivy.permute_dims(
                input_clone[batch_coor, :, d1, h0, w1], (0, 4, 1, 2, 3)
            )  # bne
            v110 = ivy.permute_dims(
                input_clone[batch_coor, :, d1, h1, w0], (0, 4, 1, 2, 3)
            )  # bsw
            v111 = ivy.permute_dims(
                input_clone[batch_coor, :, d1, h1, w1], (0, 4, 1, 2, 3)
            )  # bse

            alpha = ivy.reshape(w_coor - w0, (n, 1, to_d, to_h, to_w))
            beta = ivy.reshape(h_coor - h0, (n, 1, to_d, to_h, to_w))
            gamma = ivy.reshape(d_coor - d0, (n, 1, to_d, to_h, to_w))

            alpha = ivy.astype(alpha, ivy.float32)
            beta = ivy.astype(beta, ivy.float32)
            gamma = ivy.astype(gamma, ivy.float32)

            v = (alpha * beta * gamma) * v111
            v += ((1 - alpha) * beta * gamma) * v110
            v += (alpha * (1 - beta) * gamma) * v101
            v += ((1 - alpha) * (1 - beta) * gamma) * v100

            v += (alpha * beta * (1 - gamma)) * v011
            v += ((1 - alpha) * beta * (1 - gamma)) * v010
            v += (alpha * (1 - beta) * (1 - gamma)) * v001
            v += ((1 - alpha) * (1 - beta) * (1 - gamma)) * v000
            return v

        elif mode == "nearest":
            ceil_mask = grid_clone % 1 == 0.5
            grid_clone[ceil_mask] = ivy.astype(
                ivy.ceil(grid_clone[ceil_mask]), ivy.int64
            )

            w_coor = ivy.reshape(grid_clone[..., 0], (n, to_d, to_h, to_w))
            h_coor = ivy.reshape(grid_clone[..., 1], (n, to_d, to_h, to_w))
            d_coor = ivy.reshape(grid_clone[..., 2], (n, to_d, to_h, to_w))

            w_coor = ivy.astype(ivy.round(w_coor), ivy.int64) + 3
            h_coor = ivy.astype(ivy.round(h_coor), ivy.int64) + 3
            d_coor = ivy.astype(ivy.round(d_coor), ivy.int64) + 3
            return ivy.permute_dims(
                input_clone[batch_coor, :, d_coor, h_coor, w_coor], (0, 4, 1, 2, 3)
            )

        elif mode == "bicubic":
            raise ivy.exceptions.IvyError("Bicubic is not support in 3D grid sampling")

    else:
        raise ivy.exceptions.IvyError(f"Not supported input shape {input_clone.shape}")


def grid_sample_padding(grid, padding_mode, align_corners, borders=None):
    if padding_mode == "reflection":
        if align_corners:
            for idx, border in enumerate(borders):
                grid[..., idx] = reflect(grid[..., idx], 0, 2 * (border - 1))
                grid[..., idx] = ivy.clip(grid[..., idx], 0, border - 1)

        else:
            for idx, border in enumerate(borders):
                grid[..., idx] = reflect(grid[..., idx], -1, 2 * border - 1)
                grid[..., idx] = ivy.clip(grid[..., idx], 0, border - 1)

    elif padding_mode == "border":
        for idx, border in enumerate(borders):
            grid[..., idx] = ivy.clip(grid[..., idx], 0, border - 1)

    masks = []
    for idx, border in enumerate(borders):
        masks.append(ivy.bitwise_or(grid[..., idx] < -4, grid[..., idx] > border + 2))
        borders[idx] += 1

    zeros_mask = masks[0]
    for i in range(1, len(borders)):
        zeros_mask = ivy.bitwise_or(zeros_mask, masks[i])

    if grid[zeros_mask].shape[0] > 0:
        grid[zeros_mask] = ivy.array(borders)
    return grid



@to_ivy_arrays_and_back
def interpolate(
    input,
    size=None,
    scale_factor=None,
    mode="nearest",
    align_corners=None,
    recompute_scale_factor=None,
    antialias=False,
):
    if mode in ["nearest", "area", "nearest-exact"]:
        ivy.utils.assertions.check_exists(
            align_corners,
            inverse=True,
            message=(
                "align_corners option can only be set with the interpolating modes:"
                " linear | bilinear | bicubic | trilinear"
            ),
        )
    else:
        if not ivy.exists(align_corners):
            align_corners = False

    dim = ivy.get_num_dims(input) - 2  # Number of spatial dimensions.

    if ivy.exists(size) and ivy.exists(scale_factor):
        raise ivy.utils.exceptions.IvyException(
            "only one of size or scale_factor should be defined"
        )

    elif ivy.exists(size) and not ivy.exists(scale_factor):
        scale_factors = None

        if isinstance(size, (list, tuple)):
            ivy.utils.assertions.check_equal(
                len(size),
                dim,
                inverse=False,
                message=(
                    "Input and output must have the "
                    "same number of spatial dimensions,"
                    f" but got input with spatial dimensions of {list(input.shape[2:])}"
                    f" and output size of {size}. "
                    "Please provide input tensor in (N, C, d1, d2, ...,dK) format"
                    " and output size in (o1, o2, ...,oK) format."
                ),
                as_array=False,
            )
            output_size = size
        else:
            output_size = [size for _ in range(dim)]

    elif ivy.exists(scale_factor) and not ivy.exists(size):
        output_size = None

        if isinstance(scale_factor, (list, tuple)):
            ivy.utils.assertions.check_equal(
                len(scale_factor),
                dim,
                inverse=False,
                message=(
                    "Input and scale_factor must have the "
                    "same number of spatial dimensions,"
                    f" but got input with spatial dimensions of {list(input.shape[2:])}"
                    f" and scale_factor of shape {scale_factor}. "
                    "Please provide input tensor in (N, C, d1, d2, ...,dK) format"
                    " and scale_factor in (s1, s2, ...,sK) format."
                ),
                as_array=False,
            )
            scale_factors = scale_factor
        else:
            scale_factors = [scale_factor for _ in range(dim)]

    else:
        ivy.utils.assertions.check_any(
            [ivy.exists(size), ivy.exists(scale_factor)],
            message="either size or scale_factor should be defined",
            as_array=False,
        )

    if (
        ivy.exists(size)
        and ivy.exists(recompute_scale_factor)
        and bool(recompute_scale_factor)
    ):
        raise ivy.utils.exceptions.IvyException(
            "recompute_scale_factor is not meaningful with an explicit size."
        )

    if ivy.exists(scale_factors):
        output_size = [
            ivy.floor(ivy.shape(input)[i + 2] * scale_factors[i]) for i in range(dim)
        ]

    if (
        bool(antialias)
        and (mode not in ["bilinear", "bicubic"])
        and ivy.get_num_dims(input) == 4
    ):
        raise ivy.utils.exceptions.IvyException(
            "recompute_scale_factor is not meaningful with an explicit size."
        )

    if ivy.get_num_dims(input) == 3 and mode == "bilinear":
        raise IvyNotImplementedException(
            "Got 3D input, but bilinear mode needs 4D input"
        )
    if ivy.get_num_dims(input) == 3 and mode == "trilinear":
        raise IvyNotImplementedException(
            "Got 3D input, but trilinear mode needs 5D input"
        )
    if ivy.get_num_dims(input) == 4 and mode == "linear":
        raise IvyNotImplementedException("Got 4D input, but linear mode needs 3D input")
    if ivy.get_num_dims(input) == 4 and mode == "trilinear":
        raise IvyNotImplementedException(
            "Got 4D input, but trilinear mode needs 5D input"
        )
    if ivy.get_num_dims(input) == 5 and mode == "linear":
        raise IvyNotImplementedException("Got 5D input, but linear mode needs 3D input")
    if ivy.get_num_dims(input) == 5 and mode == "bilinear":
        raise IvyNotImplementedException(
            "Got 5D input, but bilinear mode needs 4D input"
        )

    ivy.utils.assertions.check_elem_in_list(
        ivy.get_num_dims(input),
        range(3, 6),
        message=(
            "Input Error: Only 3D, 4D and 5D input Tensors supported (got"
            f" {ivy.get_num_dims(input)}D) for the modes: nearest | linear | bilinear |"
            f" bicubic | trilinear | area | nearest-exact (got {mode})"
        ),
    )

    return ivy.interpolate(
        input, output_size, mode=mode, align_corners=align_corners, antialias=antialias
    )


def bicubic_interp(x, t, alpha=-0.75):
    n, h, w = t.shape
    coeffs = []
    coeffs.append(ivy.reshape(cubic_conv2(alpha, t + 1), (n, 1, h, w)))
    coeffs.append(ivy.reshape(cubic_conv1(alpha, t), (n, 1, h, w)))
    coeffs.append(ivy.reshape(cubic_conv1(alpha, 1 - t), (n, 1, h, w)))
    coeffs.append(ivy.reshape(cubic_conv2(alpha, 2 - t), (n, 1, h, w)))
    return x[0] * coeffs[0] + x[1] * coeffs[1] + x[2] * coeffs[2] + x[3] * coeffs[3]


def reflect(x, low2, high2):
    min = low2 / 2
    span = (high2 - low2) / 2
    x = ivy.abs(x - min)
    frac_in = ivy.abs(x / span)
    extra = (frac_in - ivy.floor(frac_in)) * ivy.abs(span)
    flips = ivy.floor(x / span)
    x[flips % 2 == 0] = (extra + min)[flips % 2 == 0]
    x[flips % 2 != 0] = (span - extra + min)[flips % 2 != 0]
    return x