import pyvista as pv
import tifffile
import numpy as np

def visualize_registration_pyvista(stl_path, tif_path, tif_threshold=10):
    print("Loading files for PyVista visualization...")
    
    # ==========================================
    # 1. LOAD THE STL
    # ==========================================
    mesh = pv.read(stl_path)

    # ==========================================
    # 2. LOAD AND CONVERT THE TIF
    # ==========================================
    tif_array = tifffile.imread(tif_path)
    tif_array[tif_array < 43400] = 0
    
    # tifffile standardly imports as (Z, Y, X). 
    # PyVista expects dimensions in (X, Y, Z), so we transpose the array.
    tif_array = np.transpose(tif_array, (2, 1, 0))

    # Create a PyVista ImageData object (a uniform grid)
    grid = pv.ImageData()
    grid.dimensions = np.array(tif_array.shape)
    
    # Flatten the array in Fortran order ("F") to properly map the XYZ values to the grid
    grid.point_data["values"] = tif_array.flatten(order="F")

    # Apply a threshold to extract only the physical structure (ignores empty background)
    # This creates a solid 3D mesh out of the active voxels
    threshed_grid = grid.threshold(tif_array.max() * 0.5)

    # ==========================================
    # 3. SET UP THE PYVISTA PLOTTER
    # ==========================================
    # Create a 1x2 side-by-side plotting layout
    plotter = pv.Plotter(shape=(1, 2))

    # --- Plot 1: STL Model ---
    plotter.subplot(0, 0)
    plotter.add_text("STL Model", font_size=12, color='black')
    plotter.add_mesh(mesh, color='cyan', show_edges=True, opacity=0.8, edge_color='gray')
    plotter.show_grid(color='black')
    plotter.add_axes()

    # --- Plot 2: TIF Stack ---
    plotter.subplot(0, 1)
    plotter.add_text(f"TIF Stack (Threshold > {tif_threshold})", font_size=12, color='black')
    plotter.add_mesh(threshed_grid, color='blue', opacity=0.8)
    plotter.show_grid(color='black')
    plotter.add_axes()

    # --- Final Settings ---
    # Link the cameras so both models rotate and zoom perfectly in sync
    plotter.link_views()
    plotter.add_axes()
    
    # Set a clean white background
    plotter.set_background('white')

    print("Rendering plots. Close the PyVista window to end the script.")
    plotter.show()


if __name__ == "__main__":
    # Update these paths to your cropped output files
    visualize_registration_pyvista(
        stl_path="test/final_cropped_model_0.5.stl",
        tif_path="test/final_cropped_image_0.5.tif",
        tif_threshold=34300  # Adjust based on your image intensity
    )