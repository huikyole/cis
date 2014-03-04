import logging
import iris
import numpy as np
from jasmin_cis.col_framework import Colocator, Constraint, Kernel
import jasmin_cis.exceptions
from jasmin_cis.data_io.hyperpoint import HyperPoint, HyperPointList
from jasmin_cis.data_io.ungridded_data import LazyData, UngriddedData, Metadata
import jasmin_cis.utils


class DefaultColocator(Colocator):

    def __init__(self, var_name='', var_long_name='', var_units=''):
        super(DefaultColocator, self).__init__()
        self.var_name = var_name
        self.var_long_name = var_long_name
        self.var_units = var_units

    def colocate(self, points, data, constraint, kernel):
        '''
            This colocator takes a list of HyperPoints and a data object (currently either Ungridded data or a Cube) and returns
             one new LazyData object with the values as determined by the constraint and kernel objects. The metadata
             for the output LazyData object is copied from the input data object.
        @param points: A list of HyperPoints
        @param data: An UngriddedData object or Cube, or any other object containing metadata that the constraint object can read
        @param constraint: An instance of a Constraint subclass which takes a data object and returns a subset of that data
                            based on it's internal parameters
        @param kernel: An instance of a Kernel subclass which takes a numberof points and returns a single value
        @return: A single LazyData object
        '''
        from jasmin_cis.data_io.ungridded_data import LazyData, UngriddedData
        import numpy as np

        metadata = data.metadata

        # Convert ungridded data to a list of points
        if isinstance(data, UngriddedData):
            data = data.get_non_masked_points()

        logging.info("--> colocating...")

        # Fill will the FillValue from the start
        values = np.zeros(len(points)) + constraint.fill_value

        for i, point in enumerate(points):
            con_points = constraint.constrain_points(point, data)
            try:
                values[i] = kernel.get_value(point, con_points)
            except ValueError:
                pass
        new_data = LazyData(values, metadata)
        if self.var_name: new_data.metadata._name = self.var_name
        if self.var_long_name: new_data.metadata.long_name = self.var_long_name
        if self.var_units: new_data.units = self.var_units
        new_data.metadata.shape = (len(points),)
        new_data.metadata.missing_value = constraint.fill_value

        return [new_data]


class AverageColocator(Colocator):

    def __init__(self, var_name='', var_long_name='', var_units='',stddev_name='',nopoints_name=''):
        super(AverageColocator, self).__init__()
        self.var_name = var_name
        self.var_long_name = var_long_name
        self.var_units = var_units
        self.stddev_name = stddev_name
        self.nopoints_name = nopoints_name

    def colocate(self, points, data, constraint, kernel):
        '''
            This colocator takes a list of HyperPoints and a data object (currently either Ungridded data or a Cube) and returns
             one new LazyData object with the values as determined by the constraint and kernel objects. The metadata
             for the output LazyData object is copied from the input data object.
        @param points: A list of HyperPoints
        @param data: An UngriddedData object or Cube, or any other object containing metadata that the constraint object can read
        @param constraint: An instance of a Constraint subclass which takes a data object and returns a subset of that data
                            based on it's internal parameters
        @param kernel: An instance of a Kernel subclass which takes a numberof points and returns a single value - This
                            should be full_average - no other kernels currently return multiple values
        @return: One LazyData object for the mean of the constrained values, one for the standard deviation and another
                    for the number of points in the constrained set for which the mean was calculated
        '''
        from jasmin_cis.data_io.ungridded_data import LazyData, UngriddedData, Metadata
        from jasmin_cis.exceptions import ClassNotFoundError

        import numpy as np

        metadata = data.metadata

        if not isinstance(kernel, full_average):
            raise ClassNotFoundError("Invalid kernel specified for this colocator. Should be 'full_average'.")

        # Convert ungridded data to a list of points
        if isinstance(data, UngriddedData):
            data = data.get_non_masked_points()

        logging.info("--> colocating...")

        # Fill will the FillValue from the start
        means = np.zeros(len(points)) + constraint.fill_value
        stddev = np.zeros(len(points)) + constraint.fill_value
        nopoints = np.zeros(len(points)) + constraint.fill_value

        for i, point in enumerate(points):
            con_points = constraint.constrain_points(point, data)
            try:
                means[i], stddev[i], nopoints[i] = kernel.get_value(point, con_points)
            except ValueError:
                pass

        mean_data = LazyData(means, metadata)
        if self.var_name:
            mean_data.metadata._name = self.var_name
        else:
            mean_data.metadata._name = mean_data.name() + '_mean'
        if self.var_long_name: mean_data.metadata.long_name = self.var_long_name
        if self.var_units: mean_data.units = self.var_units
        mean_data.metadata.shape = (len(points),)
        mean_data.metadata.missing_value = constraint.fill_value

        if not self.stddev_name:
            self.stddev_name = mean_data.name()+'_std_dev'
        stddev_data = LazyData(stddev, Metadata(name=self.stddev_name,
                                                long_name='Standard deviation from the mean in '+metadata._name,
                                                shape=(len(points),), missing_value=constraint.fill_value, units=mean_data.units))

        if not self.nopoints_name:
            self.nopoints_name = mean_data.name()+'_no_points'
        nopoints_data = LazyData(nopoints, Metadata(name=self.nopoints_name,
                                                    long_name='Number of points used to calculate the mean of '+metadata._name,
                                                    shape=(len(points),), missing_value=constraint.fill_value, units='1'))

        return [mean_data, stddev_data, nopoints_data]


class DifferenceColocator(Colocator):

    def __init__(self, var_name='', var_long_name='', var_units='', diff_name='difference', diff_long_name=''):
        super(DifferenceColocator, self).__init__()
        self.var_name = var_name
        self.var_long_name = var_long_name
        self.var_units = var_units
        self.diff_name = diff_name
        self.diff_long_name= diff_long_name

    def colocate(self, points, data, constraint, kernel):
        '''
            This colocator takes a list of HyperPoints and a data object (currently either Ungridded data or a Cube) and returns
             one new LazyData object with the values as determined by the constraint and kernel objects. The metadata
             for the output LazyData object is copied from the input data object.
        @param points: A list of HyperPoints
        @param data: An UngriddedData object or Cube, or any other object containing metadata that the constraint object can read
        @param constraint: An instance of a Constraint subclass which takes a data object and returns a subset of that data
                            based on it's internal parameters
        @param kernel: An instance of a Kernel subclass which takes a number of points and returns a single value
        @return: One LazyData object for the colocated data, and another for the difference between that data and the sample data
        '''
        from jasmin_cis.data_io.ungridded_data import LazyData, UngriddedData, Metadata
        import numpy as np

        metadata = data.metadata

        # Convert ungridded data to a list of points
        if isinstance(data, UngriddedData):
            data = data.get_non_masked_points()

        logging.info("--> colocating...")

        # Fill will the FillValue from the start
        values = np.zeros(len(points)) + constraint.fill_value
        difference = np.zeros(len(points)) + constraint.fill_value

        for i, point in enumerate(points):
            con_points = constraint.constrain_points(point, data)
            try:
                values[i] = kernel.get_value(point, con_points)
                difference[i] = values[i] - point.val[0]
            except ValueError:
                pass

        val_data = LazyData(values, metadata)
        if self.var_name: val_data.metadata._name = self.var_name
        if self.var_long_name: val_data.metadata.long_name = self.var_long_name
        if self.var_units: val_data.units = self.var_units
        val_data.metadata.shape = (len(points),)
        val_data.metadata.missing_value = constraint.fill_value

        if not self.diff_long_name: self.diff_long_name = 'Difference between given variable and sampling values'
        diff_data = LazyData(difference, Metadata(name=self.diff_name, long_name=self.diff_long_name, shape=(len(points),),
                                                  missing_value=constraint.fill_value, units=val_data.units))

        return [val_data, diff_data]


class DebugColocator(Colocator):

    def __init__(self, max_vals=1000, print_step=10.0):
        super(DebugColocator, self).__init__()
        self.max_vals = int(max_vals)
        self.print_step = float(print_step)

    def colocate(self, points, data, constraint, kernel):
        # This is the same colocate method as above with extra logging and timing steps. This is useful for debugging
        #  but will be slower than the default colocator.
        from jasmin_cis.data_io.ungridded_data import LazyData, UngriddedData
        import numpy as np
        import math
        from time import time

        metadata = data.metadata

        # Convert ungridded data to a list of points
        if isinstance(data, UngriddedData):
            data = data.get_non_masked_points()

        logging.info("--> colocating...")

        # Only colocate a certain number of points, as a quick test
        short_points = points if len(points)<self.max_vals else points[:self.max_vals-1]

        # We still need to output the full size list, to match the size of the coordinates
        values = np.zeros(len(points)) + constraint.fill_value

        times = np.zeros(len(short_points))
        for i, point in enumerate(short_points):

            t1 = time()

            # colocate using a constraint and a kernel
            con_points = constraint.constrain_points(point, data)
            try:
                values[i] = kernel.get_value(point, con_points)
            except ValueError:
                pass

            # print debug information to screen
            times[i] = time() - t1
            frac, rem = math.modf(i/self.print_step)
            if frac == 0: print str(i) + " - took: " + str(times[i]) + "s" + " -  sample: " + str(point) + " - colocated value: " + str(values[i])

        logging.info("Average time per point: " + str(np.sum(times)/len(short_points)))
        new_data = LazyData(values, metadata)
        new_data.metadata.shape = (len(points),)
        new_data.metadata.missing_value = constraint.fill_value
        return [new_data]


class DummyColocator(Colocator):

    def colocate(self, points, data, constraint, kernel):
        '''
            This colocator does no colocation at all - it just returns the original data values. This might be useful
            if the input data for one variable is already known to be on the same grid as points. This routine could
            check the coordinates are the same but currently does no such check.
        @param points: A list of HyperPoints
        @param data: An UngriddedData object or Cube
        @param constraint: Unused
        @param kernel: Unused
        @return: A single LazyData object
        '''
        from jasmin_cis.data_io.ungridded_data import LazyData

        logging.info("--> colocating...")

        new_data = LazyData(data.data, data.metadata)
        return [new_data]


class DummyConstraint(Constraint):

    def constrain_points(self, point, data):
        # This is a null constraint - all of the points just get passed back
        return data


class SepConstraint(Constraint):

    def __init__(self, h_sep=None, a_sep=None, p_sep=None, t_sep=None, fill_value=None):
        from jasmin_cis.exceptions import InvalidCommandLineOptionError

        super(SepConstraint, self).__init__()
        if fill_value is not None:
            try:
                self.fill_value = float(fill_value)
            except ValueError:
                raise InvalidCommandLineOptionError('Seperation Constraint fill_value must be a valid float')
        self.checks = []
        if h_sep is not None:
            try:
                self.h_sep = float(h_sep)
            except ValueError:
                raise InvalidCommandLineOptionError('Seperation Constraint h_sep must be a valid float')
            self.checks.append(self.horizontal_constraint)
        if a_sep is not None:
            try:
                self.a_sep = float(a_sep)
            except:
                raise InvalidCommandLineOptionError('Seperation Constraint a_sep must be a valid float')
            self.checks.append(self.alt_constraint)
        if p_sep is not None:
            try:
                self.p_sep = float(p_sep)
            except:
                raise InvalidCommandLineOptionError('Seperation Constraint p_sep must be a valid float')
            self.checks.append(self.pressure_constraint)
        if t_sep is not None:
            from jasmin_cis.time_util import parse_datetimestr_delta_to_float_days
            try:
                self.t_sep = parse_datetimestr_delta_to_float_days(t_sep)
            except ValueError as e:
                raise InvalidCommandLineOptionError(e)
            self.checks.append(self.time_constraint)

    def time_constraint(self, point, ref_point):
        return point.time_sep(ref_point) < self.t_sep

    def alt_constraint(self, point, ref_point):
        return point.alt_sep(ref_point) < self.a_sep

    def pressure_constraint(self, point, ref_point):
        return point.pres_sep(ref_point) < self.p_sep

    def horizontal_constraint(self, point, ref_point):
        return point.haversine_dist(ref_point) < self.h_sep

    def constrain_points(self, ref_point, data):
        con_points = HyperPointList()
        for point in data:
            if all(check(point, ref_point) for check in self.checks):
                con_points.append(point)
        return con_points


class mean(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using the mean of any points left after a constraint.
        '''
        from numpy import mean
        values = data.vals
        if len(values) == 0: raise ValueError
        return mean(values)


class full_average(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using the mean of any points left after a constraint. Also returns the standard
             deviation and the number of points
        '''
        from numpy import mean, std
        values = data.vals
        num_values = len(values)
        if num_values == 0: raise ValueError
        return (mean(values), std(values), num_values)


class nn_horizontal(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using nearest neighbours along the face of the earth where both points and
              data are a list of HyperPoints. The default point is the first point.
        '''
        if len(data) == 0: raise ValueError
        nearest_point = data[0]
        for data_point in data[1:]:
            if point.compdist(nearest_point, data_point): nearest_point = data_point
        return nearest_point.val[0]


class nn_altitude(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using nearest neighbours in altitude, where both points and
              data are a list of HyperPoints. The default point is the first point.
        '''
        if len(data) == 0: raise ValueError
        nearest_point = data[0]
        for data_point in data[1:]:
            if point.compalt(nearest_point, data_point): nearest_point = data_point
        return nearest_point.val[0]


class nn_pressure(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using nearest neighbours in pressure, where both points and
              data are a list of HyperPoints. The default point is the first point.
        '''
        if len(data) == 0: raise ValueError
        nearest_point = data[0]
        for data_point in data[1:]:
            if point.comppres(nearest_point, data_point): nearest_point = data_point
        return nearest_point.val[0]


class nn_time(Kernel):

    def get_value(self, point, data):
        '''
            Colocation using nearest neighbours in time, where both points and
              data are a list of HyperPoints. The default point is the first point.
        '''
        if len(data) == 0: raise ValueError
        nearest_point = data[0]
        for data_point in data[1:]:
            if point.comptime(nearest_point, data_point): nearest_point = data_point
        return nearest_point.val[0]


class nn_gridded(Kernel):
    def get_value(self, point, data):
        '''
            Co-location routine using nearest neighbour algorithm optimized for gridded data.
             This calls out to iris to do the work.
        '''
        from iris.analysis.interpolate import nearest_neighbour_data_value
        return nearest_neighbour_data_value(data, point.coord_tuple)


class li(Kernel):
    def get_value(self, point, data):
        '''
            Co-location routine using iris' linear interpolation algorithm. This only makes sense for gridded data.
        '''
        from iris.analysis.interpolate import linear
        return linear(data, point.get_coord_tuple()).data


class GriddedColocator(DefaultColocator):

    def __init__(self, var_name='', var_long_name='', var_units=''):
        super(DefaultColocator, self).__init__()
        self.var_name = var_name
        self.var_long_name = var_long_name
        self.var_units = var_units

    def colocate(self, points, data, constraint, kernel):
        '''
            This colocator takes a list of HyperPoints and a data object (currently either Ungridded data or a Cube) and returns
             one new LazyData object with the values as determined by the constraint and kernel objects. The metadata
             for the output LazyData object is copied from the input data object.
        @param points: A list of HyperPoints
        @param data: An UngriddedData object or Cube, or any other object containing metadata that the constraint object can read
        @param constraint: An instance of a Constraint subclass which takes a data object and returns a subset of that data
                            based on it's internal parameters
        @param kernel: An instance of a Kernel subclass which takes a numberof points and returns a single value
        @return: A single LazyData object
        '''
        import iris
        from jasmin_cis.exceptions import ClassNotFoundError

        if not isinstance(kernel, gridded_gridded_nn) and not isinstance(kernel, gridded_gridded_li):
            raise ClassNotFoundError("...")

        new_data = iris.analysis.interpolate.regrid(data, points, mode=kernel.name)#, **kwargs)

        return [new_data]


class gridded_gridded_nn(Kernel):
    def __init__(self):
        self.name = 'nearest'

    def get_value(self, point, data):
        '''Not needed for gridded/gridded co-location.
        '''
        return None

class gridded_gridded_li(Kernel):
    def __init__(self):
        self.name = 'bilinear'

    def get_value(self, point, data):
        '''Not needed for gridded/gridded co-location.
        '''
        return None


class UngriddedGriddedColocator(Colocator):
    """Performs co-location of ungridded data onto a the points of a cube.
    """
    def __init__(self, var_name='', var_long_name='', var_units=''):
        super(UngriddedGriddedColocator, self).__init__()
        self.var_name = var_name
        self.var_long_name = var_long_name
        self.var_units = var_units

    def colocate(self, points, data, constraint, kernel):
        """
        @param points: cube defining the sample points
        @param data: UngriddedData object providing data to be co-located
        @param constraint: instance of a Constraint subclass, which takes a data object and returns a subset of that
                           data based on it's internal parameters
        @param kernel: instance of a Kernel subclass which takes a number of points and returns a single value
        @return: Cube of co-located data
        """
        import iris
        from jasmin_cis.exceptions import ClassNotFoundError

        if not isinstance(kernel, mean):
            raise ClassNotFoundError("Expected kernel of class %s; found one of class %s", type(mean), type(kernel))

        # Work out how to iterate over the cube and map to HyperPoint coordinates.
        coord_map = self._find_standard_coords(points)
        coords = points.dim_coords
        shape = []
        output_coords = []
        for ci, coord in enumerate(coords):
            # Only iterate over coordinates used in HyperPoint.
            if ci in coord_map.values():
                if coord.ndim > 1:
                    raise NotImplementedError("Co-location of data onto a cube with a coordinate of dimension greater"
                                              " than one is not supported (coordinate %s)", coord.name())
                # Ensure that bounds exist.
                if not coord.has_bounds():
                    logging.info("Creating guessed bounds as none exist in file")
                    coord.guess_bounds()
                shape.append(coord.shape[0])
                output_coords.append(coord)

        if isinstance(data, UngriddedData):
            data = data.get_non_masked_points()

        # Initialise output array - fill will the FillValue
        #TODO Should this be a masked array?
        values = np.zeros(shape) + constraint.fill_value

        logging.info("--> Co-locating...")

        # Iterate over cells in cube.
        num_cp_coords = len(HyperPoint.standard_names)
        for indices in jasmin_cis.utils.index_iterator(shape):
            hp_values = []
            for hpi in xrange(num_cp_coords):
                if coord_map.has_key(hpi):
                    ci = coord_map[hpi]
                    hp_values.append(coords[ci].cell(indices[ci]))
                else:
                    hp_values.append(None)
            hp = HyperPoint(*hp_values)
            print hp
            con_points = constraint.constrain_points(hp, data)
            print len(con_points)
            try:
                values[indices] = kernel.get_value(hp, con_points)
            except ValueError:
                pass

        # Construct an output cube containing the colocated data.
        cube = self._create_colocated_cube(points, values, output_coords)

        return [cube]

    def _find_standard_coords(self, cube):
        """Finds the mapping of cube coordinates to the standard ones used by HyperPoint.

        @param cube: cube among the coordinates of which to find the standard coordinates
        @return: dict of index in HyperPoint to index in coords
        """
        coord_map = {}
        coord_lookup = {}
        for idx, coord in enumerate(cube.coords()):
            coord_lookup[coord] = idx

        for hpi, name in enumerate(HyperPoint.standard_names):
            coords = cube.coords(standard_name=name)
            if len(coords) > 1:
                msg = ('Expected to find exactly 1 coordinate, but found %d. They were: %s.'
                       % (len(coords), ', '.join(coord.name() for coord in coords)))
                raise jasmin_cis.exceptions.CoordinateNotFoundError(msg)
            elif len(coords) == 1:
                coord_map[hpi] = coord_lookup[coords[0]]

        return coord_map

    def _create_colocated_cube(self, src_cube, data, coords):
        """Creates a cube using the metadata from the source cube and supplied data.

        @param src_cube:
        @param data:
        @return:
        """
        dim_coords_and_dims = []
        for idx, coord in enumerate(coords):
            dim_coords_and_dims.append((coord, idx))
        cube = iris.cube.Cube(data, dim_coords_and_dims=dim_coords_and_dims)

        # cube = iris.cube.Cube(data, data, standard_name=None, long_name=None, var_name=None, units=None,
        #                       attributes=None, cell_methods=None, dim_coords_and_dims=None, aux_coords_and_dims=None,
        #                       aux_factories=None, data_manager=None)
        return cube


class CubeCellConstraint(Constraint):

    num_standard_coords = len(HyperPoint.standard_names)

    def constrain_points(self, sample_point, data):
        con_points = HyperPointList()
        for point in data:
            include = True
            for idx in xrange(CubeCellConstraint.num_standard_coords):
                cell = sample_point[idx]
                if cell is not None:
                    if not cell.contains_point(point[idx]):
                        include = False
            if include:
                con_points.append(point)
        return con_points
