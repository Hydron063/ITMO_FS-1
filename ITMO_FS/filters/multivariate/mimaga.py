import numpy as np
import random
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split


def marginal_entropy(x):
    x_counter = {xi: 0 for xi in x}
    for xi in x:
        x_counter[xi] += 1
    probs = np.array(list(map(lambda xi: x_counter[xi] / len(x), x)))
    nonzero_probs = probs[np.where(probs > 0)]
    entropy = -sum(nonzero_probs * np.log(nonzero_probs))
    return entropy


def conditional_entropy(x, y):
    y_counter = {yi: 0 for yi in y}
    x_by_y_counter = {yi: {xi: 0 for xi in x} for yi in y}
    for i in range(len(x)):
        xi = x[i]
        yi = y[i]
        y_counter[yi] += 1
        x_by_y_counter[yi][xi] += 1
    entropy = 0.
    for yi in y_counter.keys():
        x_yi = x_by_y_counter[yi].values()
        x_by_yi = np.array(list(map(lambda xi: xi / y_counter[yi], x_yi)))
        nonzero_probs = x_by_yi[np.where(x_by_yi > 0)]
        yi_entropy = -sum(nonzero_probs * np.log(nonzero_probs))
        entropy += (y_counter[yi] / len(y)) * yi_entropy
    return entropy


def mutual_information(x, y):
    return marginal_entropy(x) - conditional_entropy(x, y)


def genes_mutual_information(genes):
    """
    :param genes: dataset
    :return: mutual information for every gene in dataset
    """
    g_num, _ = genes.shape  # number of features
    mi_matrix = np.zeros((g_num, g_num))
    for i in range(g_num):
        for j in range(g_num):
            if i != j:
                mi_matrix[i][j] = mutual_information(genes[i], genes[j])
    mi_vector = [sum(mi_matrix[i]) for i in range(g_num)]
    return mi_vector


def decode_genes(mapping, chromosome, train, test):
    """
    :param chromosome: binary vector of feature presence
    :param train: train set of initial dataset
    :param test: test set of initial dataset
    :return: decoded train and test sets (reduced)
    """
    filtered_train, filtered_test = [], []
    for i in range(len(chromosome)):
        if chromosome[i] == 1:
            initial_index = mapping[i]
            filtered_train.append(train[initial_index])
            filtered_test.append(test[initial_index])
    return np.array(filtered_train), np.array(filtered_test)


def population_fitness(mapping, population, train, train_cl, test, test_cl):
    """
    :param population: vector of chromosomes
    :return: vector of (chromosome code, chromosome fitness), max fitness, average fitness
    """
    code_fitness = []
    f_sum = 0
    for i in range(len(population)):
        filtered_train, filtered_test = decode_genes(mapping, population[i], train, test)
        clf = make_pipeline(StandardScaler(), SVC(gamma='auto'))
        if len(filtered_train) == 0:
            continue
        clf.fit(filtered_train.transpose(), train_cl)
        predicted_classes = clf.predict(filtered_test.transpose())
        f = f1_score(test_cl, predicted_classes)
        code_fitness.append((population[i], f))
        f_sum += f
    code_fitness.sort(key=lambda p: p[1], reverse=True)
    f_max = code_fitness[0][1]
    f_avg = f_sum / len(population)
    return code_fitness, f_max, f_avg


def crossover(x, y):
    """ simple one-point crossover """
    random_point = random.randint(1, len(x) - 1)
    return x[0:random_point] + y[random_point:len(x)], \
           y[0:random_point] + x[random_point:len(x)]


def mutation(x):
    """ simple one-bit-inverse mutation """
    random_point = random.randint(0, len(x) - 1)
    x[random_point] = (x[random_point] - 1) % 2
    return x


def cross_and_mutate(pc, pm, population):
    """
    :param pc: crossover probability
    :param pm: mutation probability
    :param population: (chromosome code, chromosome fitness) pairs
    :return: (new population, maximum parents' fitness) pair
    """
    cross_number = int(pc * len(population))
    mutate_number = int(pm * len(population))
    max_parent_f = 0
    new_population = list(map(lambda x: x[0], population))
    for i in range(cross_number):
        parent1, f1 = population[random.randint(0, len(population) - 1)]
        parent2, f2 = population[random.randint(0, len(population) - 1)]
        child1, child2 = crossover(parent1, parent2)
        new_population.extend([child1, child2])
        max_parent_f = max([max_parent_f, f1, f2])
    for i in range(mutate_number):
        mutant = mutation(population[random.randint(0, len(population) - 1)][0])
        new_population.append(mutant)
    return new_population, max_parent_f


class MIMAGA(object):

    def __init__(self, mim_size, pop_size, max_iter, f_target, k1, k2, k3, k4):
        """
        :param mim_size: desirable number of filtered features after MIM
        :param pop_size: initial population size
        :param max_iter: maximum number of iterations in algorithm
        :param f_target: desirable fitness value
        :param k1: consts to determine crossover probability
        :param k2: consts to determine crossover probability
        :param k3: consts to determine mutation probability
        :param k4: consts to determine mutation probability
        """
        self._mim_size = mim_size
        self._pop_size = pop_size
        self._max_iter = max_iter
        self._f_target = f_target
        self._k1 = k1
        self._k2 = k2
        self._k3 = k3
        self._k4 = k4

    # MIM

    def _mim_filter(self, genes):
        """
        :param genes: initial dataset
        :return: sequence of feature indexes with minimum MI
        """
        g_num, _ = genes.shape
        mi_vector = genes_mutual_information(genes)
        seq_nums = [i for i in range(g_num)]
        target_sequence = list(map(lambda p: p[1], sorted(zip(mi_vector, seq_nums))))[:self.mim_size]
        return target_sequence

    # AGA
    def _initial_population(self):
        """
        :return: initial population
        P.S. each individual corresponds to chromosome
        """
        population = []
        for _ in range(self._pop_size):
            individual_num = random.randint(1, 2 << self._mim_size - 1)
            individual_code = list(map(int, bin(individual_num)[2:].zfill(self._mim_size)))
            population.append(individual_code)
        return population

    def _crossover_probability(self, f_max, f_avg, f_par):
        """ probability of crossover in population """
        if f_par >= f_avg:
            return self._k1 * ((f_max - f_par) / (f_max - f_avg)) \
                if f_max != f_avg else 1
        else:
            return self._k2

    def _mutation_probability(self, f_max, f_avg, f_par):
        """ probability of mutation in population """
        if f_par >= f_avg:
            return self._k3 * ((f_max - f_par) / (f_max - f_avg)) \
                if f_max != f_avg else 1
        else:
            return self._k4

    def _aga_filter(self, max_size, mapping, population, train, train_cl, test, test_cl):
        """
        :param max_size: maximum size of population (if population becomes bigger,
                         the worst individuals are killed)
        :param mapping: mapping from mim-filter index to initial index in dataset
        :param population: vector of chromosomes
        :param train: train set of initial dataset
        :param train_cl: class distribution of initial train dataset
        :param test: test set of initial dataset
        :param test_cl: class distribution of initial test dataset
        :return: best individual (sequence of features), it's fitness value
        """
        f_par = f_max = 0
        counter = 0
        best_individual = [1 for _ in range(len(population[0]))]
        while counter < self._max_iter and f_max < self._f_target:
            code_fitness, f_max, f_avg = population_fitness(mapping, population, train, train_cl, test, test_cl)
            if len(code_fitness) > max_size:
                code_fitness = code_fitness[:max_size]
                population = list(map(lambda x: x[0], code_fitness))

            highly_fitted = list(filter(lambda x: x[1] >= f_max / 2, code_fitness))
            if len(highly_fitted) == 0:
                highly_fitted = code_fitness
            best_individual = code_fitness[0][0]

            pc = self._crossover_probability(f_max, f_avg, f_par)
            pm = self._mutation_probability(f_max, f_avg, f_par)
            new_generation, f_par = cross_and_mutate(pc, pm, highly_fitted)
            population = population + new_generation
            counter += 1
        return best_individual, f_max

    def mimaga_filter(self, genes, classes):
        """
        The main function to run algorithm
        :param genes: initial dataset in format: features are rows, samples are columns
        :param classes: distribution pf initial dataset
        :return: filtered with MIMAGA dataset, fitness value
        """
        genes_T = genes.transpose()
        train_set, test_set, train_classes, test_classes = train_test_split(genes_T, classes, test_size=0.33)
        filtered_indexes = self._mim_filter(train_set.transpose())
        index_map = dict(zip([i for i in range(self._mim_size)], filtered_indexes))

        first_population = self._initial_population()
        best, max_fitness = self._aga_filter(self._pop_size * 2, index_map, first_population,
                                             train_set.transpose(), train_classes, test_set.transpose(), test_classes)
        result_genes, _ = decode_genes(index_map, best, train_set.transpose(), test_set.transpose())
        return result_genes, max_fitness


# mimaga = MIMAGA(30, 20, 20, 0.8, 0.6, 0.3, 0.9, 0.001)
# res_dataset, fitness = mimaga.mimaga_filter(dataset, distribution)
