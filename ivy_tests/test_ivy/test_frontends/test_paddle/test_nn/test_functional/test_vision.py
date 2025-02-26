# global
import ivy
from hypothesis import assume, strategies as st

# local
import ivy_tests.test_ivy.helpers as helpers
from ivy_tests.test_ivy.helpers import handle_frontend_test


# --- Helpers --- #
# --------------- #


@st.composite
def _affine_grid_helper(draw):
    align_corners = draw(st.booleans())
    dims = draw(st.integers(4, 5))
    if dims == 4:
        size = draw(
            st.tuples(
                st.integers(1, 20),
                st.integers(1, 20),
                st.integers(2, 20),
                st.integers(2, 20),
            )
        )
        theta_dtype, theta = draw(
            helpers.dtype_and_values(
                available_dtypes=helpers.get_dtypes("float"),
                min_value=0,
                max_value=1,
                shape=(size[0], 2, 3),
            )
        )
        return theta_dtype, theta[0], size, align_corners
    else:
        size = draw(
            st.tuples(
                st.integers(1, 20),
                st.integers(1, 20),
                st.integers(2, 20),
                st.integers(2, 20),
                st.integers(2, 20),
            )
        )
        theta_dtype, theta = draw(
            helpers.dtype_and_values(
                available_dtypes=helpers.get_dtypes("float"),
                min_value=0,
                max_value=1,
                shape=(size[0], 3, 4),
            )
        )
        return theta_dtype, theta[0], size, align_corners


@st.composite
def _image_shape_helper(draw, data_format):
    n = draw(helpers.ints(min_value=1, max_value=10), label="batch")
    c = draw(st.sampled_from([1, 3]), label="channel")
    h = draw(helpers.ints(min_value=1, max_value=100), label="height")
    w = draw(helpers.ints(min_value=1, max_value=100), label="width")

    if data_format == "NCHW":
        shape = (n, c, h, w)
    else:
        shape = (n, h, w, c)

    return shape


@st.composite
def grid_sample_helper(draw, dtype, mode, mode_3d, padding_mode):
    dtype = draw(dtype)
    align_corners = draw(st.booleans())
    dims = draw(st.integers(4, 5))
    height = draw(helpers.ints(min_value=5, max_value=10))
    width = draw(helpers.ints(min_value=5, max_value=10))
    channels = draw(helpers.ints(min_value=1, max_value=3))

    grid_h = draw(helpers.ints(min_value=2, max_value=4))
    grid_w = draw(helpers.ints(min_value=2, max_value=4))
    batch = draw(helpers.ints(min_value=1, max_value=5))

    padding_mode = draw(st.sampled_from(padding_mode))
    if dims == 4:
        mode = draw(st.sampled_from(mode))
        x = draw(
            helpers.array_values(
                dtype=dtype[0],
                shape=[batch, channels, height, width],
                min_value=-1,
                max_value=1,
            )
        )

        grid = draw(
            helpers.array_values(
                dtype=dtype[0],
                shape=[batch, grid_h, grid_w, 2],
                min_value=-1,
                max_value=1,
            )
        )
    elif dims == 5:
        mode = draw(st.sampled_from(mode_3d))
        depth = draw(helpers.ints(min_value=10, max_value=15))
        grid_d = draw(helpers.ints(min_value=5, max_value=10))
        x = draw(
            helpers.array_values(
                dtype=dtype[0],
                shape=[batch, channels, depth, height, width],
                min_value=-1,
                max_value=1,
            )
        )

        grid = draw(
            helpers.array_values(
                dtype=dtype[0],
                shape=[batch, grid_d, grid_h, grid_w, 3],
                min_value=-1,
                max_value=1,
            )
        )
    return dtype, x, grid, mode, padding_mode, align_corners


# --- Main --- #
# ------------ #


@handle_frontend_test(
    fn_tree="paddle.nn.functional.affine_grid",
    dtype_and_input_and_other=_affine_grid_helper(),
)
def test_paddle_affine_grid(
    *, dtype_and_input_and_other, on_device, backend_fw, fn_tree, frontend, test_flags
):
    dtype, theta, size, align_corners = dtype_and_input_and_other

    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        theta=theta,
        out_shape=size,
        align_corners=align_corners,
    )


# channel_shuffle
@handle_frontend_test(
    fn_tree="paddle.nn.functional.channel_shuffle",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=["float32", "float64"],
        shape=_image_shape_helper(data_format=st.sampled_from(["NCHW", "NHWC"])),
    ),
    groups=helpers.ints(min_value=1),
    data_format=st.sampled_from(["NCHW", "NHWC"]),
)
def test_paddle_channel_shuffle(
    *,
    dtype_and_x,
    groups,
    data_format,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    if data_format == "NCHW":
        assume(ivy.shape(x[0])[1] % groups == 0)
    else:
        assume(ivy.shape(x[0])[3] % groups == 0)
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        test_flags=test_flags,
        backend_to_test=backend_fw,
        on_device=on_device,
        frontend=frontend,
        fn_tree=fn_tree,
        x=x[0],
        groups=groups,
        data_format=data_format,
    )


@handle_frontend_test(
    fn_tree="paddle.nn.functional.grid_sample",
    dtype_x_grid_modes=grid_sample_helper(
        dtype=helpers.get_dtypes("valid", full=False),
        mode=["nearest", "bilinear", "bicubic"],
        mode_3d=["nearest", "bilinear"],
        padding_mode=["border", "zeros", "reflection"],
    ),
)
def test_paddle_grid_sample(
    *,
    dtype_x_grid_modes,
    on_device,
    backend_fw,
    fn_tree,
    frontend,
    test_flags,
):
    dtype, x, grid, mode, padding_mode, align_corners = dtype_x_grid_modes
    helpers.test_frontend_function(
        input_dtypes=dtype,
        backend_to_test=backend_fw,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        input=x,
        grid=grid,
        mode=mode,
        padding_mode=padding_mode,
        align_corners=align_corners,
    )


# pixel_shuffle
@handle_frontend_test(
    fn_tree="paddle.nn.functional.pixel_shuffle",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=["float32", "float64"],
        min_value=0,
        min_num_dims=4,
        max_num_dims=4,
        min_dim_size=3,
    ),
    factor=helpers.ints(min_value=1),
    data_format=st.sampled_from(["NCHW", "NHWC"]),
)
def test_paddle_pixel_shuffle(
    *,
    dtype_and_x,
    factor,
    data_format,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    if data_format == "NCHW":
        assume(ivy.shape(x[0])[1] % (factor**2) == 0)
    else:
        assume(ivy.shape(x[0])[3] % (factor**2) == 0)
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        x=x[0],
        upscale_factor=factor,
        data_format=data_format,
        backend_to_test=backend_fw,
    )


# pixel_unshuffle
@handle_frontend_test(
    fn_tree="paddle.nn.functional.pixel_unshuffle",
    dtype_and_x=helpers.dtype_and_values(
        available_dtypes=["float32", "float64"],
        min_value=0,
        min_num_dims=4,
        max_num_dims=4,
        min_dim_size=3,
    ),
    factor=helpers.ints(min_value=1),
    data_format=st.sampled_from(["NCHW", "NHWC"]),
)
def test_paddle_pixel_unshuffle(
    *,
    dtype_and_x,
    factor,
    data_format,
    on_device,
    fn_tree,
    frontend,
    test_flags,
    backend_fw,
):
    input_dtype, x = dtype_and_x
    if data_format == "NCHW":
        assume(ivy.shape(x[0])[2] % factor == 0)
        assume(ivy.shape(x[0])[3] % factor == 0)
    else:
        assume(ivy.shape(x[0])[1] % factor == 0)
        assume(ivy.shape(x[0])[2] % factor == 0)
    helpers.test_frontend_function(
        input_dtypes=input_dtype,
        frontend=frontend,
        test_flags=test_flags,
        fn_tree=fn_tree,
        on_device=on_device,
        x=x[0],
        downscale_factor=factor,
        data_format=data_format,
        backend_to_test=backend_fw,
    )
